import { motion } from "framer-motion";

interface ChapterTitleCardProps {
  title: string;
  /** Optional second line, faded in below the title (Phase 5 follow-up:
   * ending's "Coming soon" line). The slot below the title is always
   * reserved (even when empty), so revealing it never shifts the title. */
  subtitle?: string;
}

/**
 * Full-page black title card shown during cinematic sequences (Phase 2b
 * intro, later reused for the Phase 4a ending). Rendered underneath the
 * (still fully opaque, then fading) `ViewTransitionOverlay`.
 */
export default function ChapterTitleCard({ title, subtitle = "" }: ChapterTitleCardProps) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-3 bg-black p-4">
      <h1 className="max-w-2xl text-center font-pixel text-lg text-mm-accent md:text-2xl">
        {title}
      </h1>
      <motion.p
        initial={false}
        animate={{ opacity: subtitle ? 1 : 0 }}
        transition={{ duration: 1, ease: "easeInOut" }}
        className="max-w-2xl text-center font-pixel text-sm text-mm-highlight md:text-lg"
      >
        {subtitle || "\u00A0"}
      </motion.p>
    </div>
  );
}
