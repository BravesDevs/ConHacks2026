import { useNavigate } from 'react-router';

export default function NotFound() {
  const navigate = useNavigate();

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#F5F5F2] dark:bg-gray-900 px-8">
      <div className="text-center">
        <div className="mb-4 flex items-center justify-center gap-2">
          <div className="h-3 w-3 rounded-full bg-[#1D9E75]" />
          <span className="text-xl font-medium dark:text-white">InfraLens</span>
        </div>
        <h1 className="mb-2 text-6xl dark:text-white">404</h1>
        <p className="mb-8 text-xl text-black/60 dark:text-white/60">Page not found</p>
        <button
          onClick={() => navigate('/')}
          className="rounded-lg bg-[#1D9E75] px-6 py-3 text-white transition-opacity hover:opacity-90"
        >
          Go home
        </button>
      </div>
    </div>
  );
}
