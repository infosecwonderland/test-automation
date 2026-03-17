import fs from 'fs';
import path from 'path';

export function loadJson<T>(relativePath: string): T {
  const filePath = path.join(__dirname, '..', relativePath);
  const raw = fs.readFileSync(filePath, 'utf-8');
  return JSON.parse(raw) as T;
}

