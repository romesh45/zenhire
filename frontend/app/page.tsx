import Link from "next/link";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center px-6">
      <div className="w-full max-w-md text-center space-y-8">
        <div className="space-y-3">
          <h1 className="text-4xl font-bold tracking-tight text-gray-900">
            Zenhire
          </h1>
          <p className="text-lg text-gray-500">
            AI-powered candidate evaluation.{" "}
            <span className="text-gray-700 font-medium">Fair. Fast. Explainable.</span>
          </p>
        </div>

        <div className="flex flex-col gap-3">
          <Link
            href="/recruiter/login"
            className="w-full rounded-lg bg-gray-900 px-6 py-3 text-white font-medium text-sm hover:bg-gray-700 transition-colors"
          >
            I&apos;m a Recruiter
          </Link>
          <p className="text-xs text-gray-400">
            Have an interview link from a recruiter?
          </p>
          <p className="text-sm text-gray-500">
            Open your personalised interview link directly — it looks like{" "}
            <code className="text-xs bg-gray-100 px-1.5 py-0.5 rounded text-gray-700">
              /interview/your-session-id
            </code>
          </p>
        </div>
      </div>
    </main>
  );
}
