# Spec Center Module - Complete Implementation

## Overview
The Spec Center is a hierarchical specification and standards management system integrated into the RPMT application. It provides a professional, categorized interface for organizing, uploading, and viewing company specifications, standards, and reference documents.

## Features

### 1. **Hierarchical Category Structure**
- Multi-level nested categories (unlimited depth)
- Parent-child relationships
- Custom icons for each category
- Descriptions for better organization
- Search functionality across all categories

### 2. **File Management**
- Upload specifications (PDF, DOC, DOCX, PPTX, XLSX, XLS)
- Automatic file type detection
- File size tracking
- Metadata storage (uploader, upload date)
- Soft delete capability
- Automatic PDF conversion for Office documents

### 3. **File Preview**
- Native PDF rendering using PDF.js
- DOCX preview using Mammoth
- Fallback preview for unsupported formats
- High-quality rendering with zoom and page navigation
- Responsive design for all screen sizes

### 4. **User Interface**
- Modern, intuitive dashboard
- Collapsible category tree sidebar
- File grid with quick actions
- Responsive design (desktop, tablet, mobile)
- Admin controls for category and file management

## Database Schema

### SpecCategory Table
```
id (PK)
name (String, required)
description (Text, nullable)
parent_id (FK to SpecCategory, nullable)
icon (String, default: '📁')
order (Integer, default: 0)
is_active (Boolean, default: True)
created_at (DateTime)
updated_at (DateTime)
```

### SpecFile Table
```
id (PK)
category_id (FK to SpecCategory, required)
filename (String, unique system name)
original_name (String, original filename)
file_size (Integer)
file_type (String, e.g., 'pdf', 'docx')
storage_path (String, relative path)
description (Text, nullable)
uploaded_by (String, email)
order (Integer, default: 0)
is_active (Boolean, default: True)
created_at (DateTime)
updated_at (DateTime)
```

## API Endpoints

### Categories
- `GET /spec-center/api/categories` - Get full hierarchical structure
- `GET /spec-center/api/categories/{id}` - Get category details with files
- `POST /spec-center/api/categories` - Create new category (admin only)
- `DELETE /spec-center/api/categories/{id}` - Deactivate category (admin only)

### Files
- `GET /spec-center/api/files/{id}` - Get file information
- `GET /spec-center/api/files/{id}/preview` - Get preview page for file
- `POST /spec-center/api/files/upload` - Upload file to category (admin only)
- `DELETE /spec-center/api/files/{id}` - Delete file (admin only)
- `GET /spec-center/serve/{filename}` - Serve file for download

## File Structure

```
modules/spec_center/
├── __init__.py           # Module initialization
├── db.py                 # Database connection & setup
├── models.py             # SQLAlchemy models
└── routes.py             # API endpoints & handlers

templates/spec_center/
├── index.html            # Main dashboard
├── preview_pdf.html      # PDF viewer
├── preview_docx.html     # DOCX viewer
└── preview_unavailable.html  # Fallback

static/modules/spec_center/
└── _base.css            # Complete styling

tools/
└── seed_spec_center_categories.py  # Category initialization
```

## Initial Categories Structure

The system comes pre-configured with the following hierarchy:

1. **Customer Spec** - Customer specifications and requirements
2. **Reference Standard** - Industry standards
   - AEC-Q100 - Integrated Circuits
   - AEC-Q101 - Discrete Semiconductors
   - AEC-Q102 - Optoelectronic Semiconductors
   - AEC-Q103 - Sensors
   - AEC-Q104 - Multichip Modules
   - ISO-26262-2018 - Functional Safety
3. **Subcontractors Spec** - Subcontractor specifications
4. **Work Instruction** - Standard procedures
5. **SPEC CENTER** - Original standards
   - Audit Check List
   - Original Standard
   - Previous Standard
   - XMIND Workstation
6. **Ramschip Design Check List** - Design checklists
   - Analog Checklist
   - Digital Checklist

## Usage

### For Admin Users

#### Creating Categories
1. Click "➕ New Category" button
2. Enter category name and optional description
3. Select parent category (if sub-category)
4. Choose icon (default: 📁)
5. Click "Create"

#### Uploading Files
1. Click "📤 Upload File" button
2. Select target category
3. Drag & drop or click to select file
4. Click "Upload"
5. System automatically converts to PDF if needed

#### Deleting Content
- Click the delete icon on files to remove them
- Categories can be deactivated via API

### For All Users

#### Browsing
1. Click category in left sidebar to expand
2. Files appear in main area
3. Click file to preview or download

#### Searching
1. Use search box at top of sidebar
2. Categories filter in real-time

#### Previewing Files
1. Click 👁️ icon on any file
2. PDF appears inline with page navigation
3. DOCX displays formatted content
4. Other formats show as download prompts

#### Downloading
1. Click ⬇️ icon on any file
2. File downloads with original name

## Styling & Design

The module follows the existing design patterns:

- **Color Scheme**: Green gradient (#10b981 → #059669)
- **Typography**: Same as other modules (system fonts)
- **Spacing**: Consistent padding/margins
- **Responsive**: Works on desktop, tablet, mobile
- **Accessibility**: Semantic HTML, proper ARIA labels

## Configuration

### Supported File Types
```python
ALLOWED = {'pdf', 'pptx', 'docx', 'doc', 'xlsx', 'xls'}
```

### Upload Folder
```
uploads/spec_center/
```

### Database
```
spec_center.db  (SQLite)
```

### Logs
```
logs/spec_center.log
logs/file_deletions.log
```

## Installation & Setup

### 1. Initialize Database
```bash
cd RPMT
python tools/seed_spec_center_categories.py
```

### 2. System Requirements
- Python 3.7+
- SQLite3
- FastAPI
- SQLAlchemy
- Optional: LibreOffice (soffice) for automatic PDF conversion

### 3. Environment
Ensure these packages are in `requirements.txt`:
- fastapi
- sqlalchemy
- jinja2
- python-multipart

## PDF Conversion

The system automatically attempts to convert Office documents to PDF:

1. **Primary**: Uses LibreOffice headless mode (soffice)
2. **Secondary**: Uses Word COM on Windows
3. **Fallback**: DOCX files render in-browser using Mammoth.js

Conversion happens in background threads to avoid blocking uploads.

## Security

- **Authentication**: Session-based, requires login
- **Authorization**: Admin-only actions (create, upload, delete)
- **File Serving**: Safe file path validation
- **Audit Logging**: All deletions logged to file_deletions.log
- **Input Validation**: File type and size validation

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Mobile browsers with ES6 support

## Troubleshooting

### Files not converting to PDF
- Check if soffice is installed: `which soffice`
- Check spec_center.log for conversion errors
- Try manual conversion or upload PDF directly

### Preview not loading
- Ensure file is not corrupted
- Try downloading file first
- Check browser console for errors

### Database locked error
- Ensure no other processes are accessing spec_center.db
- Restart the application

## Future Enhancements

- [ ] Version control for documents
- [ ] Comments/annotations on files
- [ ] Full-text search in PDFs
- [ ] Bulk category import/export
- [ ] File tagging system
- [ ] Automated file organization by name patterns
- [ ] Integration with document management systems
- [ ] Advanced permission roles
- [ ] File comparison tools
- [ ] Document versioning

## Performance Considerations

- Category tree loads all hierarchy (consider pagination for 1000+ categories)
- PDF rendering limited to visible pages
- Large DOCX files (>10MB) show warning
- File uploads use streaming
- Background PDF conversion prevents blocking

## Dependencies

Core:
- fastapi
- sqlalchemy
- jinja2

Optional (for PDF conversion):
- python-pptx (if converting presentations)
- python-docx (metadata extraction)
- LibreOffice soffice binary

Frontend:
- pdf.js (CDN)
- mammoth.js (CDN)

## License & Attribution

Spec Center is part of the RPMT (Ramschip Product Management Tool) system.

---

**Created**: January 2, 2026  
**Module Status**: Complete & Production Ready
