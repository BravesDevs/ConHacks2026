import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router';
import { supabase } from '@/lib/supabase';

export default function ResetPasswordPage() {
  const navigate = useNavigate();
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [message, setMessage] = useState<{ text: string; type: 'error' | 'success' } | null>(null);
  const [loading, setLoading] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    // Supabase fires PASSWORD_RECOVERY when the reset link is followed
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event) => {
      if (event === 'PASSWORD_RECOVERY') setReady(true);
    });
    return () => subscription.unsubscribe();
  }, []);

  const handleReset = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password !== confirm) {
      setMessage({ text: 'Passwords do not match.', type: 'error' });
      return;
    }
    if (password.length < 8) {
      setMessage({ text: 'Password must be at least 8 characters.', type: 'error' });
      return;
    }
    setLoading(true);
    setMessage(null);
    const { error } = await supabase.auth.updateUser({ password });
    if (error) {
      setMessage({ text: error.message, type: 'error' });
      setLoading(false);
    } else {
      setMessage({ text: 'Password updated! Redirecting…', type: 'success' });
      setTimeout(() => navigate('/'), 1500);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#F5F5F2] dark:bg-gray-900 px-8">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <div className="mb-4 flex items-center justify-center gap-2">
            <div className="h-3 w-3 rounded-full bg-[#1D9E75]" />
            <span className="text-xl font-medium dark:text-white">InfraLens</span>
          </div>
          <h1 className="mb-2 text-3xl dark:text-white">Set new password</h1>
          <p className="text-black/60 dark:text-white/60">Choose a strong password for your account</p>
        </div>

        <form onSubmit={handleReset} className="rounded-2xl border border-black/10 dark:border-white/10 bg-white dark:bg-gray-800 p-8">
          {!ready && (
            <p className="mb-6 rounded-lg bg-amber-50 px-4 py-2.5 text-sm text-amber-700">
              Opening this page directly won't work — use the link from your reset email.
            </p>
          )}

          <div className="mb-6 space-y-4">
            <div>
              <label className="mb-2 block text-sm text-black/80 dark:text-white/80">New password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="At least 8 characters"
                disabled={!ready}
                className="w-full rounded-lg border border-black/10 dark:border-white/10 bg-white dark:bg-gray-700 dark:text-white px-4 py-2.5 outline-none transition-colors focus:border-[#1D9E75] disabled:opacity-50"
                required
              />
            </div>
            <div>
              <label className="mb-2 block text-sm text-black/80 dark:text-white/80">Confirm password</label>
              <input
                type="password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                placeholder="••••••••"
                disabled={!ready}
                className="w-full rounded-lg border border-black/10 dark:border-white/10 bg-white dark:bg-gray-700 dark:text-white px-4 py-2.5 outline-none transition-colors focus:border-[#1D9E75] disabled:opacity-50"
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
            disabled={loading || !ready}
            className="w-full rounded-lg bg-[#1D9E75] px-5 py-2.5 text-white transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            {loading ? 'Updating…' : 'Update password'}
          </button>
        </form>
      </div>
    </div>
  );
}
