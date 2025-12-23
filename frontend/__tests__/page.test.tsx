import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import Home from "../app/page";
import { useChat } from "@ai-sdk/react";

jest.mock("@ai-sdk/react", () => ({
  useChat: jest.fn(),
}));

jest.mock("ai", () => ({
  DefaultChatTransport: class {},
}));

const mockUseChat = useChat as jest.Mock;

const baseChatState = {
  messages: [],
  sendMessage: jest.fn(),
  status: "ready",
  error: null,
};

beforeEach(() => {
  localStorage.clear();
  mockUseChat.mockReturnValue(baseChatState);
});

test("renders rtl when hebrew is selected", async () => {
  localStorage.setItem("uiLanguage", "he");
  render(<Home />);

  await waitFor(() => {
    const main = document.querySelector("main");
    expect(main).toHaveAttribute("dir", "rtl");
  });
});

test("renders tool call trace with name and args", () => {
  mockUseChat.mockReturnValue({
    ...baseChatState,
    messages: [
      {
        id: "msg-1",
        role: "assistant",
        parts: [
          {
            type: "tool-call",
            toolCallId: "call-1",
            toolName: "get_medication_info",
            input: { query: "Aspirin", lang: "en" },
          },
        ],
      },
    ],
  });

  render(<Home />);

  expect(screen.getByText("get_medication_info")).toBeInTheDocument();
  expect(screen.getByText('{"query":"Aspirin"}')).toBeInTheDocument();
});

test("switching language updates stored selection", async () => {
  render(<Home />);

  const trigger = screen.getByRole("button", { name: "🇺🇸" });
  fireEvent.click(trigger);

  const russianOption = screen.getByRole("option", { name: "🇷🇺" });
  fireEvent.click(russianOption);

  await waitFor(() => {
    expect(localStorage.getItem("uiLanguage")).toBe("ru");
  });
});
