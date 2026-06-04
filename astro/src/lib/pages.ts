import fs from "node:fs/promises";
import path from "node:path";
import matter from "gray-matter";
import { marked } from "marked";

const repoRoot = path.resolve("..");

export async function readRootPage(filename: string) {
  const raw = await fs.readFile(path.join(repoRoot, filename), "utf8");
  const parsed = matter(raw);
  return {
    title: String(parsed.data.title || ""),
    html: await marked.parse(parsed.content, { async: true, gfm: true }),
  };
}
