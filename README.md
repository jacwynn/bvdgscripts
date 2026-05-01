# BVDG-VET Shopify Import Pipeline

Automated data pipeline for transforming vendor product feeds into Shopify-ready import files with optional animal product filtering.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Installation](#installation)
- [Scripts](#scripts)
- [Usage](#usage)
- [GitHub Actions](#github-actions)
- [Matrixify Integration](#matrixify-integration)
- [Troubleshooting](#troubleshooting)

---

## Overview

This pipeline automates the process of:
1. **Downloading** raw product feeds from a vendor FTP server
2. **Transforming** raw data into Shopify-compatible CSV format
3. **Splitting** products by category (jewelry types)
4. **Customizing** each category with pricing, sizing, metafields, and HTML descriptions
5. **Batching** files for Matrixify upload (5,000 rows per batch)
6. **Uploading** batches to cloud storage (currently GitHub Artifacts, with Dropbox support planned)

**Key Features:**
- ✅ Fully automated with GitHub Actions (weekly schedule + manual trigger)
- ✅ Optional animal product filtering
- ✅ Automatic vendor suffix management
- ✅ Dynamic HTML generation with size/weight lookups
- ✅ Shopify metafield support
- ✅ Error handling and notifications

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Data Flow Diagram                         │
└─────────────────────────────────────────────────────────────┘

FTP Server
    ↓
[1] filter-vet-categories.py (optional: animals only)
    ↓
Raw Feed CSV (60K+ rows)
    ↓
[2] script.py
    ├─ Transform to Shopify format
    └─ Output: root-vet-med-data-feed-YYYYMMDD.csv
    ↓
[3] split.py
    ├─ Group by Type/Category
    └─ Output: 7 category-specific CSVs
    ↓
[4] product-customization-script.py (runs 7 times, once per category)
    ├─ Clean handles & titles
    ├─ Add size/weight options
    ├─ Calculate pricing (70% of MSRP)
    ├─ Generate HTML descriptions
    ├─ Create Shopify metafields
    └─ Output: updated-shopify_import-product-feed-{category}-YYYYMMDD.csv
    ↓
[5] Batch into 5K-row files
    └─ Output: batch_1.csv, batch_2.csv, ... in YYYYMMDD/ folder
    ↓
GitHub Artifacts / Dropbox / Google Drive
    ↓
Matrixify (scheduled import to Shopify)
    ↓
Shopify Store (products updated)
```

**Categories Processed:** anklets, bracelets, chains, earrings, necklaces, pendants-&-charms, rings

---

## Installation

### Requirements

- Python 3.6+ (3.13+ recommended)
- pandas >= 2.0
- numpy >= 1.24
- google-auth-oauthlib >= 1.0.0 (for Google Drive, optional)
- google-auth-httplib2 >= 0.2.0 (for Google Drive, optional)
- google-api-python-client >= 2.80.0 (for Google Drive, optional)

### Setup

**Option A: Virtual Environment (Recommended)**

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**Option B: Global Install**

```bash
pip3 install -r requirements.txt
```

---

## Scripts

### 1. `script.py` - Raw Feed Transformation

**Purpose:** Convert raw vendor CSV to Shopify-compatible format

**Input:** Raw vendor feed CSV (from FTP)  
**Output:** `root-vet-med-data-feed-YYYYMMDD.csv`

**Transformations:**
- Create product handles from Description + Item SKU
- Build tags from Categories and ListOfSpecs
- Combine specs with weight information
- Add Shopify-required fields (Vendor, Type, Published, etc.)
- Extract image links into single `Image Src` field

**Function:**
```python
from script import run
output_path = run('./BVDG-VET/vet-med-data-feed.csv')
```

**CLI Usage:**
```bash
python3 script.py ./BVDG-VET/vet-med-data-feed.csv
```

---

### 2. `split.py` - Category Splitting

**Purpose:** Auto-split root feed by product Type into category-specific files

**Input:** `root-vet-med-data-feed-YYYYMMDD.csv`  
**Output:** 7 files:
- anklets-product-feed.csv
- bracelets-product-feed.csv
- chains-product-feed.csv
- earrings-product-feed.csv
- necklaces-product-feed.csv
- pendants-&-charms-product-feed.csv
- rings-product-feed.csv

**Function:**
```python
from split import run
category_dict = run('./BVDG-VET/root-vet-med-data-feed-20260501.csv')
# Returns: {'Anklets': './BVDG-VET/anklets-product-feed.csv', ...}
```

**CLI Usage:**
```bash
python3 split.py ./BVDG-VET/root-vet-med-data-feed-20260501.csv
```

---

### 3. `product-customization-script.py` - Category Customization

**Purpose:** Customize products per category with pricing, sizing, and HTML descriptions

**Input:** `{category}-product-feed.csv`  
**Output:** `updated-shopify_import-product-feed-{category}-YYYYMMDD.csv`

**Transformations:**
- Remove size/measurement suffixes from handles
- Clean titles of measurement text
- Calculate pricing: `Variant Price = Compare At Price * 0.7` (30% discount)
- Extract size options (length in inches, width in mm)
- Generate HTML product descriptions with embedded size/weight JSON
- Create Shopify metafields (22 fields: material, stone type, finish, etc.)
- Archive processed input to `processed-imports/`

**Function:**
```python
from product_customization_script import run
output_path = run('./BVDG-VET/bracelets-product-feed.csv', vet_medicine=False)
```

**CLI Usage:**
```bash
python3 product-customization-script.py ./BVDG-VET/bracelets-product-feed.csv
python3 product-customization-script.py ./BVDG-VET/bracelets-product-feed.csv --vet-medicine
```

---

### 4. `filter-vet-categories.py` - Animal Product Filter

**Purpose:** Extract only animal-related products from raw feed (optional preprocessing)

**Input:** Raw vendor feed CSV  
**Output:** `filtered-vet-categories-YYYYMMDD.csv` (4,459 rows from 60K)

**Logic:**
- Matches 23 animal keywords (dog, cat, bird, fish, reptiles, etc.)
- Filters Categories field for matches
- Updates Tags with only animal-related categories

**Function:**
```python
from filter_vet_categories import run
output_path = run('./BVDG-VET/vet-med-data-feed.csv')
```

**CLI Usage:**
```bash
python3 filter-vet-categories.py ./BVDG-VET/vet-med-data-feed.csv
```

---

### 5. `pipeline.py` - Full Orchestration

**Purpose:** Single entry point that runs all stages end-to-end

**Stages:**
1. Optional animal filtering
2. Transform raw feed
3. Split by category
4. Customize each category (7 runs)
5. Batch for Matrixify (5K rows per file)

**CLI Usage:**
```bash
# All products
python3 pipeline.py --input ./BVDG-VET/vet-med-data-feed.csv

# Animals only
python3 pipeline.py --input ./BVDG-VET/vet-med-data-feed.csv --animals-only

# With vet medicine vendor suffix
python3 pipeline.py --input ./BVDG-VET/vet-med-data-feed.csv --vet-medicine

# Combined
python3 pipeline.py --input ./BVDG-VET/vet-med-data-feed.csv --animals-only --vet-medicine
```

**Output:**
```
./BVDG-VET/ready-to-import/YYYYMMDD/
├── batch_1.csv (5000 rows)
├── batch_2.csv (5000 rows)
├── ...
└── batch_N.csv (remaining rows)
```

---

## Usage

### Local Usage

**1. Prepare raw feed**
```bash
# Place vendor CSV at:
./BVDG-VET/vet-med-data-feed.csv
```

**2. Run pipeline**
```bash
source venv/bin/activate  # Activate venv if using one
python3 pipeline.py --input ./BVDG-VET/vet-med-data-feed.csv
```

**3. Find output**
```
./BVDG-VET/ready-to-import/20260501/
├── batch_1.csv
├── batch_2.csv
└── ...
```

**4. Download and upload to Shopify/Matrixify**

---

### Folder Structure

```
BVDG-VET/
├── vet-med-data-feed.csv              ← Input (raw vendor feed)
├── root-vet-med-data-feed-*.csv       ← Stage 2 output
├── anklets-product-feed.csv           ← Stage 3 outputs (7 files)
├── bracelets-product-feed.csv
├── ...
├── processed-imports/                 ← Archive of processed inputs
│   ├── anklets-product-feed.csv
│   ├── bracelets-product-feed.csv
│   └── ...
└── ready-to-import/
    └── YYYYMMDD/                      ← Batched for Matrixify
        ├── batch_1.csv
        ├── batch_2.csv
        └── ...
```

---

## GitHub Actions

### Setup

**1. Push to GitHub**
```bash
git add .
git commit -m "Add pipeline and GitHub Actions workflow"
git push
```

**2. Add Secrets**
Go to **GitHub Repo → Settings → Secrets and variables → Actions**

Required secrets:
```
FTP_SERVER           = ftp.vendor.com
FTP_USER             = your_username
FTP_PASS             = your_password
FTP_FILE_PATH        = /path/to/9947_Extract_2.csv
```

Optional (for cloud upload later):
```
GOOGLE_DRIVE_CREDENTIALS    = (JSON service account key)
GOOGLE_DRIVE_FOLDER_ID      = (folder ID from URL)
DROPBOX_ACCESS_TOKEN        = (Dropbox app token)
DROPBOX_FOLDER_PATH         = /BVDG-VET-Imports
```

### Running the Workflow

**Automatic (Weekly)**
- Triggers every Monday at 9:00 AM UTC
- Downloads from FTP, runs pipeline, stores artifacts

**Manual Trigger**
1. Go to **Actions** tab in GitHub
2. Click **"BVDG-VET Import Pipeline"**
3. Click **"Run workflow"**
4. Choose options:
   - `animals_only`: true/false
5. Click **"Run workflow"**

### Downloading Results

1. Go to **Actions** tab
2. Click the workflow run
3. Scroll to **Artifacts**
4. Download `matrixify-batches-***`
5. Unzip to get batch CSVs

---

## Matrixify Integration

### Manual Import (Current)

1. **Download batches** from GitHub Actions artifacts
2. **Go to Matrixify** in your Shopify admin
3. **Click Import**
4. **Upload batch CSV** (batch_1.csv, batch_2.csv, etc.)
5. **Review and confirm**
6. Repeat for each batch

### Automated Import (Future)

When using Dropbox or Google Drive:

**1. Set up Matrixify import**
- In Matrixify, click **Import**
- Select **Dropbox** or **Google Drive**
- Choose **BVDG-VET-Imports** folder
- Select CSV files

**2. Schedule imports**
- Set to run **Monday 10:00 AM** (after pipeline completes at 9:00 AM)
- Set to **auto-repeat weekly**
- Enable **auto-skip if files unchanged** (optional)

**3. Monitor**
- Matrixify will import each batch file
- Products update in Shopify automatically
- Check Matrixify logs for errors

---

## Configuration

### Vendor Suffix

Control whether products are marked as vet medicine:

```bash
# Quality Gold (default)
python3 pipeline.py --input ./BVDG-VET/vet-med-data-feed.csv

# Quality Gold - Vet Medicine
python3 pipeline.py --input ./BVDG-VET/vet-med-data-feed.csv --vet-medicine
```

Shopify uses this to create collections:
- **Collection Filter:** Vendor = "Quality Gold - Vet Medicine"

### Pricing

**Current:** `Variant Price = Variant Compare At Price * 0.7` (30% discount)

To change, edit in `product-customization-script.py` line 155:
```python
df['Variant Price'] = df['Variant Compare At Price'] * 0.7  # Change 0.7 here
```

### Categories

**Default 7 categories** (hardcoded in `split.py`):
- anklets
- bracelets
- chains
- earrings
- necklaces
- pendants-&-charms
- rings

To modify, edit `split.py` line 30:
```python
allowed_categories = ['your-category-1', 'your-category-2', ...]
```

---

## Troubleshooting

### `ModuleNotFoundError: No module named 'pandas'`
**Solution:** Install dependencies
```bash
pip3 install -r requirements.txt
```

### `SyntaxError: invalid syntax` (f-strings)
**Solution:** Use Python 3.6+
```bash
python3 --version  # Should be 3.6 or higher
python3 pipeline.py --input ...  # Use python3, not python
```

### FTP Connection Fails
**Check:**
- FTP server address is correct
- Username/password are correct
- File path exists on server
- Network/firewall allows FTP

### Google Drive Upload 403 Error
**Solution:** Use Dropbox instead (service accounts lack Drive storage quota)

### Shopify Import Shows Errors
**Check:**
- Required columns present: Handle, Title, Description, Vendor, Type, Tags, Published, Variant SKU, Variant Price, Variant Compare At Price, Variant Grams
- No empty required fields
- File encoding is UTF-8
- Row count matches batch file

### Products Not Grouped into Collections
**Check in Shopify:**
1. Create collection with rule: `Vendor = Quality Gold - Vet Medicine`
2. Verify vendor suffix was applied (check imported product details)
3. Run import again with `--vet-medicine` flag

---

## Future Enhancements

- [ ] Dropbox automated upload
- [ ] Google Sheets integration
- [ ] Delta detection (only update changed products)
- [ ] Shopify API direct import
- [ ] Real-time sync (not just scheduled)
- [ ] Product image upload
- [ ] Inventory sync from vendor
- [ ] Email notifications with summary report
- [ ] Webhook triggers from FTP server
- [ ] Support for multiple vendor feeds

---

## Support

**For issues:**
1. Check the Troubleshooting section
2. Review GitHub Actions logs (Actions tab → workflow run)
3. Check error messages in pipeline output
4. Verify all secrets are set correctly

**For questions:**
- See inline comments in script files
- Check function docstrings
- Review Shopify/Matrixify documentation

---

## Version History

- **v1.0** (2026-05-01): Initial release
  - Core pipeline with 5 scripts
  - GitHub Actions workflow
  - GitHub Artifacts storage
  - Support for animal product filtering

