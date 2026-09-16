export type Execution = 'auto' | 'sync' | 'async';
export type ExtractionMode = 'rules' | 'ai' | 'auto';

export interface ExtractionOptions {
  schema?: 'thai_official_letter';
  mode?: ExtractionMode;
  execution?: Execution;
  idempotencyKey?: string;
}

export interface Job {
  id: string;
  status: 'queued' | 'processing' | 'succeeded' | 'failed' | 'expired';
  progress: number;
  schema_name: string;
  execution: string;
}

export class ThaiDocClient {
  constructor(private readonly baseUrl = 'http://localhost:8000', private readonly apiKey?: string) {}

  async extract(file: Blob, options: ExtractionOptions = {}): Promise<unknown> {
    const form = new FormData();
    form.append('file', file);
    form.append('schema', options.schema ?? 'thai_official_letter');
    form.append('mode', options.mode ?? 'auto');
    form.append('execution', options.execution ?? 'auto');
    const headers: Record<string, string> = {};
    if (this.apiKey) headers['X-API-Key'] = this.apiKey;
    if (options.idempotencyKey) headers['Idempotency-Key'] = options.idempotencyKey;
    const response = await fetch(`${this.baseUrl}/v1/extractions`, { method: 'POST', headers, body: form });
    if (!response.ok) throw await response.json();
    return response.json();
  }

  async job(id: string): Promise<Job> {
    const response = await fetch(`${this.baseUrl}/v1/jobs/${id}`, {
      headers: this.apiKey ? { 'X-API-Key': this.apiKey } : {}
    });
    if (!response.ok) throw await response.json();
    return response.json() as Promise<Job>;
  }
}

