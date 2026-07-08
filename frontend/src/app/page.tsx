import { UploadForm } from "@/components/upload/UploadForm";

export default function Home() {
  return (
    <main className="flex min-h-[calc(100vh-4rem)] flex-col items-center bg-vellum-50 px-6 py-16 dark:bg-print-900">
      <div className="mb-10 text-center">
        <h1 className="mt-3 font-display text-4xl text-graphite-900 dark:text-linework">
          Isometric MTO Extractor
        </h1>
        <p className="mx-auto mt-3 max-w-md text-sm text-graphite-700/70 dark:text-linework-dim">
          Upload a piping isometric drawing to begin the material takeoff pipeline.
        </p>
      </div>

      <UploadForm />
    </main>
  );
}
