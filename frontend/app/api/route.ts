import { createUIMessageStreamResponse } from 'ai';
import { createParser } from 'eventsource-parser';

const decoder = new TextDecoder();

const createChunkId = () =>
  `chunk-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;

export async function POST(req: Request) {
  const payload = await req.json();
  const messages = Array.isArray(payload?.messages)
    ? payload.messages
    : Array.isArray(payload?.body?.messages)
      ? payload.body.messages
      : [];
  const language = payload?.language ?? payload?.body?.language;
  const conversationId = payload?.conversationId ?? payload?.body?.conversationId;
  const id = payload?.id ?? payload?.body?.id;
  const apiBaseUrl = process.env.API_BASE_URL ?? 'http://localhost:8000';
  const userIdHeader = req.headers.get('x-user-id');
  const userIdFromBody =
    payload?.userId ??
    payload?.user_id ??
    payload?.body?.userId ??
    payload?.body?.user_id;
  const effectiveUserId = userIdHeader ?? userIdFromBody ?? null;

  const simplifiedMessages = Array.isArray(messages)
    ? messages
        .map((message: any) => {
          const parts = Array.isArray(message?.parts) ? message.parts : [];
          const partsContent = parts
            .filter((part: any) => part?.type === 'text' && typeof part.text === 'string')
            .map((part: any) => part.text)
            .join('');
          const fallbackContent =
            typeof message?.content === 'string' ? message.content : '';
          const content = partsContent || fallbackContent;

          return {
            role: message?.role ?? 'user',
            content,
          };
        })
        .filter((message: any) => message.content)
    : [];

  const backendResponse = await fetch(`${apiBaseUrl}/chat/completions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
      ...(effectiveUserId ? { 'x-user-id': effectiveUserId } : {}),
    },
    body: JSON.stringify({
      messages: simplifiedMessages,
      language: language ?? 'auto',
      conversation_id: conversationId ?? id ?? null,
      user_id: effectiveUserId ?? undefined,
    }),
  });

  if (!backendResponse.ok) {
    return new Response('Backend chat endpoint failed', { status: 502 });
  }
  const responseBody = backendResponse.body;
  if (!responseBody) {
    return new Response('Backend chat endpoint failed', { status: 502 });
  }

  const stream = new ReadableStream({
    async start(controller) {
      const textPartId = createChunkId();
      const toolCallStreamId = createChunkId();
      let textStarted = false;
      const toolCallAccumulator = new Map<
        string,
        { id: string; name: string | null; args: string }
      >();
      const toolCallIndexMap = new Map<number, string>();
      const executedToolCalls = new Set<string>();

      const flushToolCalls = () => {
        if (!toolCallAccumulator.size) return;
        for (const toolCall of toolCallAccumulator.values()) {
          if (executedToolCalls.has(toolCall.id)) {
            continue;
          }
          if (!toolCall.args.trim()) {
            continue;
          }
          const toolName = toolCall.name ?? 'tool-call';
          let input: unknown = {};
          if (toolCall.args.trim()) {
            try {
              input = JSON.parse(toolCall.args);
            } catch {
              input = { raw: toolCall.args };
            }
          }
          controller.enqueue({
            type: 'tool-input-available',
            toolCallId: toolCall.id,
            toolName,
            input,
          });
        }
        toolCallAccumulator.clear();
      };

      const parser = createParser((event) => {
        if (event.type !== 'event') return;

        const message = event.data;
        if (!message) return;

        if (message === '[DONE]') {
          flushToolCalls();
          if (textStarted) {
            controller.enqueue({ type: 'text-end', id: textPartId });
          }
          controller.close();
          return;
        }

        try {
          const payload = JSON.parse(message);
          const delta = payload?.choices?.[0]?.delta ?? {};
          const finishReason = payload?.choices?.[0]?.finish_reason;
          const toolExecution = payload?.tool_execution;

          if (delta.content) {
            if (!textStarted) {
              controller.enqueue({ type: 'text-start', id: textPartId });
              textStarted = true;
            }
            controller.enqueue({
              type: 'text-delta',
              id: textPartId,
              delta: delta.content,
            });
          }

          if (toolExecution?.id && toolExecution?.name) {
            executedToolCalls.add(toolExecution.id);
            controller.enqueue({
              type: 'tool-input-available',
              toolCallId: toolExecution.id,
              toolName: toolExecution.name,
              input: toolExecution.arguments ?? {},
            });
          }

          if (delta.tool_calls?.length) {
            delta.tool_calls.forEach((toolCall: any, index: number) => {
              let toolCallId = toolCall.id;
              if (!toolCallId) {
                toolCallId = toolCallIndexMap.get(index);
                if (!toolCallId) {
                  toolCallId = `${toolCallStreamId}-${index}`;
                  toolCallIndexMap.set(index, toolCallId);
                }
              }
              const entry = toolCallAccumulator.get(toolCallId) ?? {
                id: toolCallId,
                name: null,
                args: '',
              };
              const fn = toolCall.function ?? {};
              if (fn.name) {
                entry.name = fn.name;
              }
              if (fn.arguments) {
                entry.args += fn.arguments;
              }
              toolCallAccumulator.set(toolCallId, entry);
            });
          }

          if (finishReason) {
            flushToolCalls();
          }
        } catch (error) {
          controller.enqueue({ type: 'error', errorText: 'stream_parse_error' });
        }
      });

      const reader = responseBody.getReader();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        parser.feed(decoder.decode(value, { stream: true }));
      }

      flushToolCalls();
      if (textStarted) {
        controller.enqueue({ type: 'text-end', id: textPartId });
      }
      controller.close();
    },
  });

  return createUIMessageStreamResponse({ stream });
}
