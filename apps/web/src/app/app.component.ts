import { JsonPipe, NgIf } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import {
  IonBadge, IonButton, IonCard, IonCardContent, IonCardHeader, IonCardTitle,
  IonContent, IonHeader, IonIcon, IonProgressBar, IonSpinner, IonTitle, IonToolbar
} from '@ionic/angular';
import { addIcons } from 'ionicons';
import { cloudUploadOutline, documentTextOutline, downloadOutline } from 'ionicons/icons';

interface ExtractionJob {
  id: string;
  status: 'queued' | 'processing' | 'succeeded' | 'failed' | 'expired';
  progress: number;
  error_detail?: string;
}

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    JsonPipe, NgIf, IonBadge, IonButton, IonCard, IonCardContent, IonCardHeader,
    IonCardTitle, IonContent, IonHeader, IonIcon, IonProgressBar, IonSpinner,
    IonTitle, IonToolbar
  ],
  templateUrl: './app.component.html'
})
export class AppComponent {
  private readonly http = inject(HttpClient);
  readonly file = signal<File | null>(null);
  readonly result = signal<unknown>(null);
  readonly error = signal('');
  readonly loading = signal(false);
  readonly progress = signal(0);
  readonly jobStatus = signal('');

  constructor() {
    addIcons({ cloudUploadOutline, documentTextOutline, downloadOutline });
  }

  choose(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.file.set(input.files?.[0] ?? null);
    this.result.set(null);
    this.error.set('');
  }

  extract(): void {
    const file = this.file();
    if (!file) return;
    const body = new FormData();
    body.append('file', file);
    body.append('schema', 'thai_official_letter');
    body.append('mode', 'auto');
    body.append('execution', 'auto');
    this.loading.set(true);
    this.http.post('/api/v1/extractions', body).subscribe({
      next: value => {
        if (this.isJob(value)) {
          this.poll(value.id);
        } else {
          this.result.set(value);
          this.loading.set(false);
        }
      },
      error: response => {
        this.error.set(response.error?.detail ?? 'Extraction failed');
        this.loading.set(false);
      }
    });
  }

  private isJob(value: unknown): value is ExtractionJob {
    return typeof value === 'object' && value !== null && 'id' in value && 'status' in value;
  }

  private poll(id: string): void {
    this.http.get<ExtractionJob>(`/api/v1/jobs/${id}`).subscribe({
      next: job => {
        this.progress.set(job.progress / 100);
        this.jobStatus.set(job.status);
        if (job.status === 'succeeded') {
          this.http.get(`/api/v1/jobs/${id}/result`).subscribe({
            next: result => { this.result.set(result); this.loading.set(false); },
            error: () => { this.error.set('Could not load the completed result'); this.loading.set(false); }
          });
        } else if (job.status === 'failed' || job.status === 'expired') {
          this.error.set(job.error_detail ?? `Job ${job.status}`);
          this.loading.set(false);
        } else {
          window.setTimeout(() => this.poll(id), 1000);
        }
      },
      error: () => { this.error.set('Could not read job status'); this.loading.set(false); }
    });
  }

  download(): void {
    const blob = new Blob([JSON.stringify(this.result(), null, 2)], { type: 'application/json' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = 'thaidoc-result.json';
    link.click();
    URL.revokeObjectURL(link.href);
  }
}
