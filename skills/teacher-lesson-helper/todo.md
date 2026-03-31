# Project TODO

## Database & Schema
- [x] Create textbooks table (지도서 관리)
- [x] Create lesson_extractions table (차시 추출 데이터)
- [x] Create recent_accesses table (최근 접근 이력)
- [x] Run database migrations

## Backend - PDF Processing
- [x] Setup PDF text extraction library (pdfjs-dist)
- [x] Implement PDF text extraction function
- [x] Implement lesson number auto-detection algorithm
- [x] Create lesson parsing and storage logic

## Backend - API Routes
- [x] textbook.list - List user's textbooks
- [x] textbook.create - Upload new textbook
- [x] textbook.getById - Get textbook details
- [x] textbook.delete - Delete textbook
- [x] lesson.getByNumber - Get lesson by number
- [x] lesson.listByTextbook - List all lessons in textbook
- [x] lesson.downloadPdf - Download lesson as PDF
- [x] recentAccess.list - Get recent access history
- [x] recentAccess.add - Record access history (integrated in lesson.getByNumber)

## Frontend - Pages
- [x] Create Dashboard page (main page with textbook list) - TextbookList.tsx
- [x] Create TextbookUpload page (PDF upload form) - integrated in TextbookList
- [x] Create LessonViewer page (view and extract lessons) - TextbookDetail.tsx
- [x] Create RecentAccess component (quick access to recent lessons)

## Frontend - Components
- [x] TextbookCard component (display textbook info) - in TextbookList.tsx
- [x] PDFUploadForm component (file upload with validation) - in TextbookList.tsx
- [x] LessonExtractor component (lesson number input and display) - in TextbookDetail.tsx
- [x] LessonContent component (display extracted content) - in TextbookDetail.tsx
- [x] DownloadButton component (PDF download) - in TextbookDetail.tsx

## Testing
- [x] Write tests for PDF text extraction
- [x] Write tests for lesson parsing logic
- [ ] Write tests for API endpoints
- [ ] Test file upload and S3 integration

## Deployment & Final
- [ ] Test full workflow end-to-end
- [x] Create checkpoint before publishing
- [ ] Deploy to production
