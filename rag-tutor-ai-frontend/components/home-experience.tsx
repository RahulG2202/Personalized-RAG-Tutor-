"use client";

import { ChangeEvent, useEffect, useRef, useState } from "react";
import gsap from "gsap";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type StatusTone = "idle" | "working" | "success" | "error";

export default function HomeExperience() {
  const rootRef = useRef<HTMLElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<string>("No file selected");
  const [status, setStatus] = useState("Tutor ready");
  const [tone, setTone] = useState<StatusTone>("idle");
  const [isTraining, setIsTraining] = useState(false);

  useEffect(() => {
    const ctx = gsap.context(() => {
      gsap.from("[data-animate='rise']", {
        y: 34,
        opacity: 0,
        duration: 0.8,
        ease: "power3.out",
        stagger: 0.08
      });

      gsap.to("[data-animate='float']", {
        y: -12,
        duration: 2.2,
        ease: "sine.inOut",
        repeat: -1,
        yoyo: true,
        stagger: 0.2
      });
    }, rootRef);

    return () => ctx.revert();
  }, []);

  async function handleTrainTutor() {
    setIsTraining(true);
    setTone("working");
    setStatus("Training tutor");

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/v1/ingest/run-ingestion?reset_db=false`,
        { method: "POST" }
      );

      if (!response.ok) {
        throw new Error(`Training failed with status ${response.status}`);
      }

      const data = (await response.json()) as {
        files_processed?: string[];
        total_pages_extracted?: number;
      };

      const fileCount = data.files_processed?.length ?? 0;
      const pageCount = data.total_pages_extracted ?? 0;
      setTone("success");
      setStatus(`Trained ${fileCount} file${fileCount === 1 ? "" : "s"} - ${pageCount} pages`);
    } catch {
      setTone("error");
      setStatus("Training failed");
    } finally {
      setIsTraining(false);
    }
  }

  function handleMaterialChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];

    if (!file) {
      setSelectedFile("No file selected");
      return;
    }

    setSelectedFile(file.name);
    setTone("success");
    setStatus("Material selected");
  }

  const statusClass = {
    idle: "bg-chalk text-ink",
    working: "bg-lemon text-ink",
    success: "bg-aqua text-ink",
    error: "bg-tomato text-chalk"
  }[tone];

  return (
    <main ref={rootRef} className="min-h-screen overflow-hidden px-5 py-5 sm:px-8 lg:px-10">
      <header
        data-animate="rise"
        className="flex items-center justify-between border-b-2 border-ink pb-4"
      >
        <p className="text-sm font-black uppercase tracking-normal">RAG Tutor AI</p>
        <p className="hidden text-sm font-bold uppercase tracking-normal sm:block">
          Learn from your own library
        </p>
      </header>

      <section className="grid min-h-[calc(100vh-82px)] grid-rows-[auto_1fr] gap-8 py-8 lg:grid-cols-[1.08fr_0.92fr] lg:grid-rows-1 lg:items-center lg:gap-10">
        <div className="flex flex-col justify-center">
          <p
            data-animate="rise"
            className="mb-4 w-fit border-2 border-ink bg-lemon px-3 py-1 text-xs font-black uppercase tracking-normal shadow-crisp"
          >
            Personalized study engine
          </p>

          <h1
            data-animate="rise"
            className="max-w-5xl text-[clamp(4.5rem,14vw,12rem)] font-black uppercase leading-[0.78] tracking-normal"
          >
            RAG
            <span className="block text-tomato">Tutor</span>
            <span className="block">AI</span>
          </h1>

          <p
            data-animate="rise"
            className="mt-7 max-w-xl text-lg font-semibold leading-8 text-graphite sm:text-xl"
          >
            Train a focused AI tutor on your PDFs, then ask questions that stay grounded in your material.
          </p>
        </div>

        <div data-animate="rise" className="flex items-center">
          <section className="w-full border-2 border-ink bg-chalk p-4 shadow-crisp sm:p-6">
            <div className="mb-5 flex items-start justify-between gap-4">
              <div>
                <h2 className="text-3xl font-black uppercase leading-none sm:text-5xl">
                  Tutor Studio
                </h2>
                <p className="mt-3 text-sm font-bold uppercase tracking-normal text-graphite">
                  {selectedFile}
                </p>
              </div>
              <span className={`border-2 border-ink px-3 py-2 text-xs font-black uppercase ${statusClass}`}>
                {status}
              </span>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <button
                type="button"
                onClick={handleTrainTutor}
                disabled={isTraining}
                className="min-h-40 border-2 border-ink bg-ink p-5 text-left text-chalk transition-transform hover:-translate-y-1 disabled:cursor-not-allowed disabled:opacity-70"
              >
                <span className="block text-sm font-black uppercase tracking-normal">
                  Action 01
                </span>
                <span className="mt-8 block text-3xl font-black uppercase leading-none">
                  {isTraining ? "Training" : "Train Tutor"}
                </span>
              </button>

              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="min-h-40 border-2 border-ink bg-aqua p-5 text-left text-ink transition-transform hover:-translate-y-1"
              >
                <span className="block text-sm font-black uppercase tracking-normal">
                  Action 02
                </span>
                <span className="mt-8 block text-3xl font-black uppercase leading-none">
                  Upload Material
                </span>
              </button>

              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,application/pdf"
                className="sr-only"
                onChange={handleMaterialChange}
              />
            </div>

            <div className="mt-5 grid gap-4 sm:grid-cols-3">
              {["Extract", "Embed", "Teach"].map((item, index) => (
                <div
                  key={item}
                  data-animate="float"
                  className={`border-2 border-ink p-4 ${
                    index === 0
                      ? "bg-lemon"
                      : index === 1
                        ? "bg-paper"
                        : "bg-tomato text-chalk"
                  }`}
                >
                  <p className="text-xs font-black uppercase tracking-normal">
                    Step 0{index + 1}
                  </p>
                  <p className="mt-6 text-2xl font-black uppercase leading-none">
                    {item}
                  </p>
                </div>
              ))}
            </div>
          </section>
        </div>
      </section>
    </main>
  );
}
