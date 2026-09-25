/** Locate diary entries without treating headings inside fenced code as entries. */
export function diarySections(content) {
  const sections = [];
  let offset = 0;
  let fence = null;
  let frontmatter = content.startsWith('---\n') || content.startsWith('---\r\n');
  for (const line of content.match(/[^\n]*\n|[^\n]+$/g) || []) {
    const plain = line.replace(/\r?\n$/, '');
    if (frontmatter) {
      if (offset > 0 && plain === '---') frontmatter = false;
    } else {
      const marker = plain.match(/^ {0,3}(`{3,}|~{3,})(.*)$/);
      if (fence) {
        if (marker && marker[1][0] === fence[0] && marker[1].length >= fence.length && !marker[2].trim()) fence = null;
      } else if (marker) {
        fence = marker[1];
      } else {
        const heading = plain.match(/^## ([0-2]\d:[0-5]\d)\s*$/);
        if (heading) sections.push({ time: heading[1], start: offset, bodyStart: offset + line.length });
      }
    }
    offset += line.length;
  }
  return sections.map((section, index) => {
    const end = sections[index + 1]?.start ?? content.length;
    return { ...section, end, text: content.slice(section.bodyStart, end).trim() };
  });
}

export function replaceDiarySection(existing, editing, replacement) {
  if (!existing || existing.sha !== editing.sha) {
    throw new Error('この日記は別の端末などで変更されています。本文をコピーしてから、投稿済みの項目を取得し直してください。');
  }
  const section = diarySections(existing.content)[editing.index];
  if (!section || section.time !== editing.time) throw new Error('編集する項目が見つかりません。取得し直してください。');
  return existing.content.slice(0, section.start) + replacement.trimStart().trimEnd() + '\n\n' + existing.content.slice(section.end);
}
