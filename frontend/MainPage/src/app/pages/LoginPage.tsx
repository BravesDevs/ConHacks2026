import { useState } from 'react';
import { useNavigate } from 'react-router';
import { supabase } from '@/lib/supabase';

type View = 'login' | 'forgot';

export default function LoginPage() {
  const navigate = useNavigate();
  const [view, setView] = useState<View>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState<{ text: string; type: 'error' | 'success' } | null>(null);
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setMessage(null);
    setLoading(true);
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) {
      setMessage({ text: error.message, type: 'error' });
      setLoading(false);
    } else {
      navigate('/');
    }
  };

  const handleSignUp = async (e: React.MouseEvent) => {
    e.preventDefault();
    if (!email || !password) {
      setMessage({ text: 'Enter an email and password first to sign up.', type: 'error' });
      return;
    }
    setMessage(null);
    setLoading(true);
    const { error } = await supabase.auth.signUp({ email, password });
    if (error) {
      setMessage({ text: error.message, type: 'error' });
    } else {
      setMessage({ text: 'Check your email to confirm your account.', type: 'success' });
    }
    setLoading(false);
  };

  const handleForgotPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) {
      setMessage({ text: 'Enter your email address.', type: 'error' });
      return;
    }
    setMessage(null);
    setLoading(true);
    const { error } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/reset-password`,
    });
    if (error) {
      setMessage({ text: error.message, type: 'error' });
    } else {
      setMessage({ text: 'Password reset link sent — check your inbox.', type: 'success' });
    }
    setLoading(false);
  };

  const switchView = (next: View) => {
    setView(next);
    setMessage(null);
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#F5F5F2] dark:bg-gray-900 px-8">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <div className="mb-4 flex items-center justify-center gap-2">
            <div className="h-3 w-3 rounded-full bg-[#1D9E75]" />
            <span className="text-xl font-medium dark:text-white">InfraLens</span>
          </div>
          <h1 className="mb-2 text-3xl dark:text-white">
            {view === 'login' ? 'Welcome back' : 'Reset password'}
          </h1>
          <p className="text-black/60 dark:text-white/60">
            {view === 'login'
              ? 'Sign in to your account to continue'
              : "We'll send a reset link to your email"}
          </p>
        </div>

        {view === 'login' ? (
          <form onSubmit={handleLogin} className="rounded-2xl border border-black/10 dark:border-white/10 bg-white dark:bg-gray-800 p-8">
            <div className="mb-6 space-y-4">
              <div>
                <label className="mb-2 block text-sm text-black/80 dark:text-white/80">Email address</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@company.com"
                  className="w-full rounded-lg border border-black/10 dark:border-white/10 bg-white dark:bg-gray-700 dark:text-white px-4 py-2.5 outline-none transition-colors focus:border-[#1D9E75]"
                  required
                />
              </div>
              <div>
                <label className="mb-2 block text-sm text-black/80 dark:text-white/80">Password</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full rounded-lg border border-black/10 dark:border-white/10 bg-white dark:bg-gray-700 dark:text-white px-4 py-2.5 outline-none transition-colors focus:border-[#1D9E75]"
                  required
                />
              </div>
            </div>

            {message && (
              <p className={`mb-4 rounded-lg px-4 py-2.5 text-sm ${message.type === 'error' ? 'bg-red-50 text-red-600' : 'bg-[#1D9E75]/10 text-[#1D9E75]'}`}>
                {message.text}
              </p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-lg bg-[#1D9E75] px-5 py-2.5 text-white transition-opacity hover:opacity-90 disabled:opacity-50"
            >
              {loading ? 'Signing in…' : 'Sign in'}
            </button>

            <div className="mt-4 text-center text-sm text-black/60 dark:text-white/60">
              <button
                type="button"
                onClick={() => switchView('forgot')}
                className="text-[#1D9E75] hover:underline"
              >
                Forgot password?
              </button>
            </div>
          </form>
        ) : (
          <form onSubmit={handleForgotPassword} className="rounded-2xl border border-black/10 dark:border-white/10 bg-white dark:bg-gray-800 p-8">
            <div className="mb-6">
              <label className="mb-2 block text-sm text-black/80 dark:text-white/80">Email address</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@company.com"
                className="w-full rounded-lg border border-black/10 dark:border-white/10 bg-white dark:bg-gray-700 dark:text-white px-4 py-2.5 outline-none transition-colors focus:border-[#1D9E75]"
                required
              />
            </div>

            {message && (
              <p className={`mb-4 rounded-lg px-4 py-2.5 text-sm ${message.type === 'error' ? 'bg-red-50 text-red-600' : 'bg-[#1D9E75]/10 text-[#1D9E75]'}`}>
                {message.text}
              </p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-lg bg-[#1D9E75] px-5 py-2.5 text-white transition-opacity hover:opacity-90 disabled:opacity-50"
            >
              {loading ? 'Sending…' : 'Send reset link'}
            </button>

            <div className="mt-4 text-center text-sm text-black/60 dark:text-white/60">
              <button
                type="button"
                onClick={() => switchView('login')}
                className="text-[#1D9E75] hover:underline"
              >
                ← Back to sign in
              </button>
            </div>
          </form>
        )}

        {view === 'login' && (
          <p className="mt-6 text-center text-sm text-black/60 dark:text-white/60">
            Don't have an account?{' '}
            <a href="#" onClick={handleSignUp} className="text-[#1D9E75] hover:underline">
              Sign up
            </a>
          </p>
        )}
      </div>
    </div>
  );
}
