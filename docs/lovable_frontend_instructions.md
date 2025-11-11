# Lovable Frontend Instructions
## LepSoc Season Summary Validation System

### PROJECT OVERVIEW
Build a web application for validating Lepidopterist Society annual observation submissions. The app will upload Excel/CSV files, validate data through a Python backend, allow human review of flagged items, and download corrected files.

---

## DESIGN REQUIREMENTS

### Color Scheme
- Primary: Deep Purple (#6B46C1) - representing butterflies
- Secondary: Forest Green (#22C55E) - representing nature
- Accent: Amber (#F59E0B) - for warnings
- Error: Red (#EF4444)
- Background: Light Gray (#F9FAFB)
- Text: Dark Gray (#111827)

### Typography
- Headers: Inter or Poppins
- Body: Inter or Open Sans
- Monospace (for data): JetBrains Mono or Fira Code

---

## COMPONENTS TO BUILD

### 1. Layout Component (`AppLayout.tsx`)
```tsx
// Main application shell
- Fixed header with logo and title
- Navigation menu (Upload, Review, History)
- Main content area
- Footer with version info
```

### 2. File Upload Component (`FileUpload.tsx`)
```tsx
interface FileUploadProps {
  onFileSelect: (file: File) => void;
  acceptedFormats: string[];
  maxSize: number; // in MB
}

// Features:
- Drag-and-drop zone
- File type validation (.xlsx, .csv)
- File size validation (max 10MB)
- Preview first 10 rows in a table
- Column header validation
- Upload button
- Cancel/Clear button
```

### 3. Validation Progress Component (`ValidationProgress.tsx`)
```tsx
interface ValidationProgressProps {
  validationId: string;
  totalRows: number;
  processedRows: number;
  errors: number;
  warnings: number;
  status: 'processing' | 'review' | 'complete' | 'error';
}

// Features:
- Progress bar with percentage
- Real-time row counter
- Error/warning badges
- Estimated time remaining
- Cancel validation button
- Live status updates via WebSocket
```

### 4. Review Table Component (`ReviewTable.tsx`)
```tsx
interface ReviewItem {
  rowIndex: number;
  field: string;
  originalValue: string;
  suggestedValue: string;
  errorType: 'error' | 'warning';
  message: string;
}

// Features:
- Paginated data table (10 items per page)
- Color coding (red for errors, yellow for warnings)
- Inline editing for corrections
- Accept/Reject/Modify buttons per row
- Bulk actions (Accept All, Reject All)
- Filter by error type
- Search functionality
- Export review items
```

### 5. Field Details Panel (`FieldDetailsPanel.tsx`)
```tsx
// Shows details for selected field
- Field name and description
- Validation rules
- Original value
- Suggested correction
- Confidence score
- iNaturalist lookup results (if applicable)
- Edit input with validation
```

### 6. Metadata Viewer Component (`MetadataViewer.tsx`)
```tsx
interface ValidationMetadata {
  validationId: string;
  fileName: string;
  totalRows: number;
  errors: number;
  warnings: number;
  corrections: number;
  newStateRecords: Array<{species: string, state: string}>;
  newCountyRecords: Array<{species: string, county: string}>;
}

// Features:
- Summary statistics cards
- New records highlights
- Change log table
- Validation timeline
- Export metadata as JSON
```

### 7. Download Results Component (`DownloadResults.tsx`)
```tsx
interface DownloadOptions {
  format: 'xlsx' | 'csv' | 'json';
  includeMetadata: boolean;
  includeOriginalValues: boolean;
}

// Features:
- Format selection dropdown
- Options checkboxes
- Download button
- Preview validated data
- Email results option
```

### 8. Record Badge Component (`RecordBadge.tsx`)
```tsx
// Special badge for new state/county records
interface RecordBadgeProps {
  type: 'state' | 'county';
  species: string;
  location: string;
}

// Shows celebratory badge for new records
```

---

## PAGES TO CREATE

### 1. Upload Page (`/upload`)
```tsx
// Main upload interface
- FileUpload component
- Instructions panel
- Sample file download link
- Recent uploads list
```

### 2. Validation Page (`/validation/:id`)
```tsx
// Active validation monitoring
- ValidationProgress component
- Live log viewer
- Pause/Resume controls
- Preliminary results
```

### 3. Review Page (`/review/:id`)
```tsx
// Human review interface
- ReviewTable component
- FieldDetailsPanel (sidebar)
- Action buttons (Save, Submit, Export)
- Progress indicator for review completion
```

### 4. Results Page (`/results/:id`)
```tsx
// Final results and download
- MetadataViewer component
- DownloadResults component
- Validation report
- Share results link
```

### 5. History Page (`/history`)
```tsx
// Past validations
- Table of previous validations
- Filter by date, status, user
- Re-run validation option
- Download past results
```

---

## API INTEGRATION

### API Service (`api/validationService.ts`)
```typescript
const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export const validationAPI = {
  // Upload file for validation
  uploadFile: async (file: File): Promise<{validationId: string}> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await fetch(`${API_BASE}/api/validate/upload`, {
      method: 'POST',
      body: formData
    });
    return response.json();
  },

  // Get validation status
  getStatus: async (validationId: string): Promise<ValidationStatus> => {
    const response = await fetch(`${API_BASE}/api/validate/status/${validationId}`);
    return response.json();
  },

  // Get items for review
  getReviewItems: async (validationId: string, page: number = 1): Promise<ReviewResponse> => {
    const response = await fetch(`${API_BASE}/api/validate/review/${validationId}?page=${page}`);
    return response.json();
  },

  // Submit corrections
  submitCorrections: async (validationId: string, corrections: any): Promise<void> => {
    await fetch(`${API_BASE}/api/validate/approve/${validationId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(corrections)
    });
  },

  // Download results
  downloadResults: async (validationId: string, format: string): Promise<Blob> => {
    const response = await fetch(`${API_BASE}/api/validate/download/${validationId}?format=${format}`);
    return response.blob();
  }
};
```

### WebSocket Service (`api/websocketService.ts`)
```typescript
export class ValidationWebSocket {
  private ws: WebSocket | null = null;

  connect(validationId: string, onMessage: (data: any) => void) {
    this.ws = new WebSocket(`ws://localhost:8000/ws/${validationId}`);
    
    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      onMessage(data);
    };
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}
```

---

## STATE MANAGEMENT (Zustand)

### Store (`store/validationStore.ts`)
```typescript
import create from 'zustand';

interface ValidationStore {
  currentValidation: ValidationState | null;
  reviewItems: ReviewItem[];
  metadata: ValidationMetadata | null;
  
  // Actions
  setCurrentValidation: (validation: ValidationState) => void;
  updateProgress: (progress: Partial<ValidationState>) => void;
  setReviewItems: (items: ReviewItem[]) => void;
  updateReviewItem: (index: number, updates: Partial<ReviewItem>) => void;
  setMetadata: (metadata: ValidationMetadata) => void;
}

export const useValidationStore = create<ValidationStore>((set) => ({
  // ... implementation
}));
```

---

## KEY INTERACTIONS

### 1. File Upload Flow
```
1. User drags file into upload zone
2. System validates file format and structure
3. Shows preview of first 10 rows
4. User confirms and clicks "Start Validation"
5. File uploads to backend
6. Redirects to validation progress page
```

### 2. Review Flow
```
1. System flags rows with errors/warnings
2. User navigates to review page
3. User reviews each flagged item
4. User can: Accept suggestion, Modify, or Reject
5. User submits all corrections
6. System applies corrections
7. User proceeds to download results
```

### 3. Real-time Updates
```
1. WebSocket connects on validation start
2. Backend sends row-by-row progress
3. UI updates progress bar and counters
4. Errors/warnings appear in real-time
5. User can pause/resume validation
```

---

## RESPONSIVE DESIGN

### Breakpoints
```css
- Mobile: < 640px
- Tablet: 640px - 1024px
- Desktop: > 1024px
```

### Mobile Adaptations
- Stack upload zone vertically
- Simplify review table (key fields only)
- Use bottom sheet for field details
- Swipe actions for accept/reject

---

## ACCESSIBILITY

### Requirements
- ARIA labels on all interactive elements
- Keyboard navigation support
- Focus indicators
- Screen reader announcements for status changes
- High contrast mode support
- Error messages linked to form fields

### Keyboard Shortcuts
- `Enter` - Accept suggestion
- `Delete` - Reject suggestion
- `Tab` - Navigate fields
- `Ctrl+S` - Save progress
- `Ctrl+D` - Download results
- `Arrow keys` - Navigate table

---

## ERROR HANDLING

### User-Friendly Messages
```typescript
const ERROR_MESSAGES = {
  UPLOAD_FAILED: "Failed to upload file. Please check your connection and try again.",
  INVALID_FORMAT: "File format not supported. Please upload .xlsx or .csv files.",
  FILE_TOO_LARGE: "File exceeds 10MB limit. Please reduce file size.",
  VALIDATION_FAILED: "Validation encountered an error. Our team has been notified.",
  CONNECTION_LOST: "Connection lost. Attempting to reconnect...",
};
```

### Error States
- Show inline errors below fields
- Toast notifications for system errors
- Retry buttons where applicable
- Graceful degradation for lost connections

---

## ANIMATIONS

### Micro-interactions
- File upload: Smooth progress fill
- Row validation: Slide in from right
- Error highlight: Gentle pulse
- Success: Check mark animation
- New record: Confetti animation

### Transitions
```css
/* Smooth page transitions */
transition: all 0.3s ease;

/* Progress bar animation */
@keyframes progress-fill {
  from { width: 0; }
  to { width: var(--progress); }
}

/* Error pulse */
@keyframes error-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
```

---

## SAMPLE COMPONENT CODE

### FileUpload Component Example
```tsx
import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, X, FileSpreadsheet } from 'lucide-react';

export const FileUpload: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<any[]>([]);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const file = acceptedFiles[0];
    if (file) {
      setFile(file);
      // Parse and preview file
      previewFile(file);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'text/csv': ['.csv']
    },
    maxSize: 10 * 1024 * 1024, // 10MB
    multiple: false
  });

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div
        {...getRootProps()}
        className={`
          border-2 border-dashed rounded-lg p-12 text-center
          transition-colors cursor-pointer
          ${isDragActive ? 'border-purple-500 bg-purple-50' : 'border-gray-300 hover:border-gray-400'}
        `}
      >
        <input {...getInputProps()} />
        <FileSpreadsheet className="mx-auto h-16 w-16 text-gray-400 mb-4" />
        {isDragActive ? (
          <p className="text-lg">Drop the file here...</p>
        ) : (
          <>
            <p className="text-lg mb-2">Drag & drop your file here</p>
            <p className="text-sm text-gray-500">or click to browse</p>
            <p className="text-xs text-gray-400 mt-2">Supports .xlsx and .csv (max 10MB)</p>
          </>
        )}
      </div>

      {file && (
        <div className="mt-6 p-4 bg-green-50 rounded-lg">
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <FileSpreadsheet className="h-8 w-8 text-green-600 mr-3" />
              <div>
                <p className="font-medium">{file.name}</p>
                <p className="text-sm text-gray-500">
                  {(file.size / 1024 / 1024).toFixed(2)} MB
                </p>
              </div>
            </div>
            <button
              onClick={() => setFile(null)}
              className="p-2 hover:bg-green-100 rounded-full"
            >
              <X className="h-5 w-5 text-gray-500" />
            </button>
          </div>
        </div>
      )}

      {preview.length > 0 && (
        <div className="mt-6">
          <h3 className="font-medium mb-3">Preview (first 10 rows)</h3>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              {/* Table implementation */}
            </table>
          </div>
        </div>
      )}

      <div className="mt-6 flex gap-4">
        <button
          disabled={!file}
          className="px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
        >
          Start Validation
        </button>
        <button
          className="px-6 py-3 border border-gray-300 rounded-lg hover:bg-gray-50"
        >
          Download Sample File
        </button>
      </div>
    </div>
  );
};
```

---

## TESTING CHECKLIST

- [ ] File upload works for .xlsx and .csv
- [ ] File size validation (reject > 10MB)
- [ ] Column header validation
- [ ] Progress updates in real-time
- [ ] Review table displays errors correctly
- [ ] Inline editing works
- [ ] Accept/Reject buttons function
- [ ] Download in all formats
- [ ] WebSocket reconnection
- [ ] Mobile responsive design
- [ ] Keyboard navigation
- [ ] Screen reader compatibility

---

## DEPLOYMENT NOTES

1. Environment variables needed:
   - `REACT_APP_API_URL` - Backend API URL
   - `REACT_APP_WS_URL` - WebSocket URL
   - `REACT_APP_VERSION` - App version

2. Build optimization:
   - Enable code splitting
   - Lazy load heavy components
   - Optimize images
   - Enable gzip compression

3. Production checklist:
   - SSL certificates
   - CORS configuration
   - Error tracking (Sentry)
   - Analytics (Google Analytics)
   - Performance monitoring

---

This specification provides everything needed to build the frontend in Lovable. Focus on creating a clean, intuitive interface that makes the validation process smooth and efficient for users.
