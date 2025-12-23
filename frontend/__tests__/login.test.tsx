/**
 * Frontend tests for login functionality
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import LoginPage from '../app/login/page';

// Mock useRouter
const mockPush = jest.fn();
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush
  })
}));

global.fetch = jest.fn();

describe('Login Page', () => {
  beforeEach(() => {
    (fetch as jest.Mock).mockClear();
    mockPush.mockClear();
    localStorage.clear();
  });

  test('renders login form', () => {
    render(<LoginPage />);

    expect(screen.getByText('Log in')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Email')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Password')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /log in/i })).toBeInTheDocument();
  });

  test('successful login redirects to chat', async () => {
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        token: 'USER001',
        name: 'Adi Himelbloy',
        user_id: 'USER001',
        email: 'adi.himelbloy@example.com'
      })
    });

    render(<LoginPage />);

    // Fill in form
    fireEvent.change(screen.getByPlaceholderText('Email'), {
      target: { value: 'adi.himelbloy@example.com' }
    });
    fireEvent.change(screen.getByPlaceholderText('Password'), {
      target: { value: 'demo123' }
    });

    // Submit
    fireEvent.click(screen.getByRole('button', { name: /log in/i }));

    // Check redirect
    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/');
    });

    // Check localStorage
    expect(localStorage.getItem('authToken')).toBe('USER001');
    expect(localStorage.getItem('authName')).toBe('Adi Himelbloy');
  });

  test('failed login shows error message', async () => {
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      text: async () => 'Invalid email or password'
    });

    render(<LoginPage />);

    fireEvent.change(screen.getByPlaceholderText('Email'), {
      target: { value: 'wrong@example.com' }
    });
    fireEvent.change(screen.getByPlaceholderText('Password'), {
      target: { value: 'wrongpassword' }
    });

    fireEvent.click(screen.getByRole('button', { name: /log in/i }));

    // Check error appears
    await waitFor(() => {
      expect(screen.getByText(/Invalid email or password/i)).toBeInTheDocument();
    });
  });

  test('disables button when fields are empty', () => {
    render(<LoginPage />);

    const button = screen.getByRole('button', { name: /log in/i });
    expect(button).toBeDisabled();
  });

  test('enables button when both fields are filled', () => {
    render(<LoginPage />);

    fireEvent.change(screen.getByPlaceholderText('Email'), {
      target: { value: 'test@example.com' }
    });
    fireEvent.change(screen.getByPlaceholderText('Password'), {
      target: { value: 'password' }
    });

    const button = screen.getByRole('button', { name: /log in/i });
    expect(button).not.toBeDisabled();
  });

  test('shows loading state during login', async () => {
    (fetch as jest.Mock).mockImplementation(() =>
      new Promise(resolve => setTimeout(resolve, 100))
    );

    render(<LoginPage />);

    fireEvent.change(screen.getByPlaceholderText('Email'), {
      target: { value: 'test@example.com' }
    });
    fireEvent.change(screen.getByPlaceholderText('Password'), {
      target: { value: 'password' }
    });

    fireEvent.click(screen.getByRole('button', { name: /log in/i }));

    // Check loading text
    expect(screen.getByText('Signing in...')).toBeInTheDocument();
  });
});
