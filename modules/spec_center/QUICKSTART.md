# Spec Center - Quick Start Guide

## What's New

The **Spec Center** module is a complete hierarchical specification and standards management system. It allows you to:

✅ Organize specifications into unlimited nested categories  
✅ Upload and manage PDF, DOC, DOCX, PPTX, XLSX documents  
✅ Preview files inline with PDF viewers and document renderers  
✅ Search across all categories  
✅ Download specifications for offline use  

## Getting Started

### Step 1: Initialize Categories

Run the seed script to create the initial category structure:

```bash
cd "c:\Users\이상원\Downloads\QMS\Python-Project\RPMT"
python tools/seed_spec_center_categories.py
```

You should see:
```
✅ Spec Center categories initialized successfully!
Created XX categories
```

### Step 2: Start the Application

```bash
uvicorn app:app --reload
```

### Step 3: Access Spec Center

1. Open: `http://localhost:8000`
2. Navigate to **Spec Center** in the sidebar
3. You'll see the category tree on the left

## Key Features

### 📁 Category Management (Admin Only)

**Create a Category:**
- Click the **➕ New Category** button
- Fill in: Name, Description (optional), Icon, Parent Category
- Click **Create**

**Edit Hierarchy:**
- Categories support unlimited nesting
- Each category shows file count badge

### 📤 Upload Files (Admin Only)

**Upload Specification:**
- Click **📤 Upload File** button
- Select target category
- Drag & drop file OR click to browse
- Supported: PDF, DOC, DOCX, PPTX, XLSX, XLS
- System auto-converts Office docs to PDF

### 👁️ View & Preview

**Browse Files:**
- Click any category to see its files
- Files display in a clean grid layout

**Preview:**
- Click **👁️** icon to preview inline
- PDFs show with page navigation
- DOCX renders formatted HTML
- Click **⬇️** to download

**Search:**
- Type in search box at top
- Results filter in real-time

## Interface Layout

```
┌─────────────────────────────────────────────────┐
│  Spec-Center       [➕ New Category] [📤 Upload] │
│  Company Specs                                   │
├──────────────┬────────────────────────────────────┤
│ 📁 Categories│ Category Header                    │
│              │ ───────────────────────────────    │
│ ▶ Customer   │ 📄 Files in this Category          │
│ ▼ Reference  │ ┌──────┬──────┬──────────────────┐│
│   ▶ AEC-Q100 │ │📕 PDF│📘 DOC│ [Preview][Down] ││
│   ▶ AEC-Q101 │ └──────┴──────┴──────────────────┘│
│ ▶ Subcontr.  │ Preview Area...                   │
│ ▶ Instruction│ (Shows inline preview on click)   │
│ ▶ SPEC CENTER│                                   │
│ ▶ Design CL  │                                   │
│              │                                   │
└──────────────┴────────────────────────────────────┘
```

## Default Categories

The system comes with these pre-built categories:

1. **Customer Spec** - Customer requirements
2. **Reference Standard** - Industry standards (AEC-Q, ISO-26262)
3. **Subcontractors Spec** - Vendor specifications
4. **Work Instruction** - Procedures
5. **SPEC CENTER** - Original company standards
6. **Ramschip Design Check List** - Design checklists

You can add more categories or reorganize as needed!

## Common Tasks

### Upload a Quality Standard

1. Click **📤 Upload File**
2. Select "Reference Standard" → "AEC-Q100"
3. Select your PDF file
4. Click **Upload**
5. Done! File is now available in the category

### Find a Specification

1. Type keywords in **🔍 Search specs** box
2. Categories filter as you type
3. Click matching category
4. Files appear in main area

### Share a Document

1. Click **👁️** on the file to preview
2. Share URL: `http://server/spec-center`
3. Viewers can find and preview documents

### Manage Admin Functions

- **Create categories**: Admin → Category menu
- **Upload files**: Admin → Upload button
- **Delete files**: Admin → File delete icon
- **View logs**: Check `logs/file_deletions.log`

## File Format Support

| Format | Preview | Convert | Notes |
|--------|---------|---------|-------|
| PDF | ✅ Native | - | Best for archival |
| DOCX | ✅ Mammoth | ✅ → PDF | Formatted rendering |
| DOC | ❌ Download | ✅ → PDF | If converter available |
| PPTX | ❌ Download | ✅ → PDF | Use PDF for best results |
| XLSX | ❌ Download | ✅ → PDF | Large files may be slow |
| XLS | ❌ Download | ✅ → PDF | Legacy format |

## Database & Storage

**Database**: `spec_center.db` (SQLite)  
**Files**: `uploads/spec_center/` directory  
**Logs**: `logs/spec_center.log`  

Files are stored with timestamps to prevent conflicts:
```
20260102_143025_RS-COP-01.pdf
20260102_143105_AEC-Q100.xlsx
```

## Troubleshooting

### Database not created?
```bash
python tools/seed_spec_center_categories.py
```

### Files not appearing?
1. Check category was selected during upload
2. Verify file type is allowed
3. Check `logs/spec_center.log` for errors

### PDF not converting?
1. LibreOffice may not be installed
2. Try uploading as PDF directly
3. Or contact admin to install soffice

### Preview not loading?
1. Try refreshing page
2. Check browser console (F12)
3. Ensure file is not corrupted

## API Reference

Quick reference for API calls:

```bash
# Get all categories
curl http://localhost:8000/spec-center/api/categories

# Get category files
curl http://localhost:8000/spec-center/api/categories/1

# Download file
wget http://localhost:8000/spec-center/serve/20260102_143025_RS-COP-01.pdf
```

## Style Consistency

The Spec Center uses the same design system as other modules:

- **Primary Color**: Green (#10b981)
- **Accent**: Dark Green (#059669)
- **Fonts**: System fonts (clean, readable)
- **Spacing**: Consistent padding/margins
- **Responsive**: Mobile-friendly design

## Performance Tips

1. **Large PDFs**: May take time to render. Be patient!
2. **Many categories**: Consider organizing at 2-3 levels
3. **Bulk uploads**: Upload files one-by-one or in small batches
4. **Search**: Works best with 100-1000 categories

## Next Steps

1. ✅ Initialize database (done with seed script)
2. ✅ Access the application
3. 📋 Create your category structure
4. 📤 Upload your specifications
5. 👥 Share with team members
6. 🔍 Use search to find documents

---

**Need Help?**
- Check the full [README.md](README.md) for technical details
- Review logs: `logs/spec_center.log`
- Check database: `spec_center.db`

**Version**: 1.0.0  
**Date**: January 2, 2026
