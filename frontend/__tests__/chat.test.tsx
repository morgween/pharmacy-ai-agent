/**
 * Frontend tests for chat functionality
 * Run with: npm test
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import ChatPage from '../app/page';

// Mock fetch for API calls
global.fetch = jest.fn();

describe('Chat Interface', () => {
  beforeEach(() => {
    // Reset mocks
    (fetch as jest.Mock).mockClear();
    localStorage.clear();
  });

  test('renders chat interface with default language', () => {
    render(<ChatPage />);

    // Check title
    expect(screen.getByText('Pharmacy AI Agent')).toBeInTheDocument();

    // Check language selector shows English flag
    expect(screen.getByText('🇺🇸')).toBeInTheDocument();

    // Check input placeholder
    expect(screen.getByPlaceholderText(/Ask about meds/i)).toBeInTheDocument();
  });

  test('switches language to Hebrew', () => {
    render(<ChatPage />);

    // Click Hebrew language option
    const hebrewOption = screen.getByText('🇮🇱');
    fireEvent.click(hebrewOption);

    // Check title changed to Hebrew
    expect(screen.getByText('סוכן בית מרקחת AI')).toBeInTheDocument();
  });

  test('displays user message after sending', async () => {
    render(<ChatPage />);

    const input = screen.getByPlaceholderText(/Ask about meds/i);
    const sendButton = screen.getByRole('button', { name: /send/i });

    // Type message
    fireEvent.change(input, { target: { value: 'Is Aspirin available?' } });

    // Send message
    fireEvent.click(sendButton);

    // Check user message appears
    await waitFor(() => {
      expect(screen.getByText('Is Aspirin available?')).toBeInTheDocument();
    });
  });

  test('shows tool execution panel when tools are called', async () => {
    // Mock streaming response
    (fetch as jest.Mock).mockImplementation(() =>
      Promise.resolve({
        ok: true,
        body: {
          getReader: () => ({
            read: jest.fn()
              .mockResolvedValueOnce({
                done: false,
                value: new TextEncoder().encode('data: {"tool_execution":{"name":"get_medication_info","arguments":{"query":"Aspirin"}}}\n\n')
              })
              .mockResolvedValueOnce({
                done: true
              })
          })
        }
      })
    );

    render(<ChatPage />);

    const input = screen.getByPlaceholderText(/Ask about meds/i);
    fireEvent.change(input, { target: { value: 'Tell me about Aspirin' } });
    fireEvent.click(screen.getByRole('button', { name: /send/i }));

    // Check tools panel appears
    await waitFor(() => {
      expect(screen.getByText('Tools')).toBeInTheDocument();
    });
  });

  test('displays login button when not authenticated', () => {
    render(<ChatPage />);

    expect(screen.getByText('Log in')).toBeInTheDocument();
  });

  test('displays user name when authenticated', () => {
    // Set auth token in localStorage
    localStorage.setItem('authToken', 'USER001');
    localStorage.setItem('authName', 'Adi Himelbloy');

    render(<ChatPage />);

    expect(screen.getByText(/Signed in: Adi Himelbloy/i)).toBeInTheDocument();
    expect(screen.getByText('Log out')).toBeInTheDocument();
  });
});


describe('Multilingual Support', () => {
  const languages = [
    { code: 'en', flag: '🇺🇸', title: 'Pharmacy AI Agent' },
    { code: 'he', flag: '🇮🇱', title: 'סוכן בית מרקחת AI' },
    { code: 'ru', flag: '🇷🇺', title: 'Фарм AI-ассистент' },
    { code: 'ar', flag: '🇸🇦', title: 'وكيل صيدلية بالذكاء الاصطناعي' }
  ];

  languages.forEach(({ code, flag, title }) => {
    test(`renders correctly in ${code}`, () => {
      render(<ChatPage />);

      // Switch language
      fireEvent.click(screen.getByText(flag));

      // Check title
      expect(screen.getByText(title)).toBeInTheDocument();
    });
  });
});


describe('Tool Call Display', () => {
  test('shows tool arguments correctly', async () => {
    // Mock tool execution event
    (fetch as jest.Mock).mockImplementation(() =>
      Promise.resolve({
        ok: true,
        body: {
          getReader: () => ({
            read: jest.fn()
              .mockResolvedValueOnce({
                done: false,
                value: new TextEncoder().encode('data: {"tool_execution":{"id":"call_123","name":"get_medication_info","arguments":{"query":"Aspirin","lang":"en"}}}\n\n')
              })
              .mockResolvedValueOnce({
                done: true
              })
          })
        }
      })
    );

    render(<ChatPage />);

    const input = screen.getByPlaceholderText(/Ask about meds/i);
    fireEvent.change(input, { target: { value: 'What is Aspirin?' } });
    fireEvent.click(screen.getByRole('button', { name: /send/i }));

    await waitFor(() => {
      expect(screen.getByText('get_medication_info')).toBeInTheDocument();
      expect(screen.getByText(/Aspirin/)).toBeInTheDocument();
    });
  });
});
