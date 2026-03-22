# TROUBLESHOOTING GUIDE: Clustering Not Working in Streamlit

## Current Status
- ✅ Python/CLI clustering works perfectly (test_full_workflow.py passes)
- ❌ Streamlit web interface clustering fails/crashes
- 🟢 Streamlit running on 0.0.0.0:8501

## Step 1: Check Session State (CRITICAL!)
**Navigate to:** http://192.168.100.229:8501 → Click **Debug - Session State**

This page will show you:
- ✅ OR ❌ Whether `adata` exists in session
- ✅ OR ❌ Whether data shape is correct
- All current session variables

**What to look for:**
- If it says `❌ adata is None`, the data isn't flowing through properly
- If shape shows `0 × 0`, data is corrupted

---

## Step 2: Test Data Flow (Sequential)
Follow **exactly** this order:

### 2A. Upload Data
1. Go to **Upload Data** page
2. Click **"🔬 Load PBMC 3k"** (demo dataset)
3. Wait for ✅ success message
4. You should see: `✅ PBMC 3k loaded — 2,700 cells × 2,000 genes`

### 2B. Quality Control
1. Go to **Quality Control** page
2. You should see QC graphs
3. Click **"▶ Run Quality Control Filter"** button
4. Wait for ✅ success message
5. You should see: `✅ QC complete — ...`

### 2C. Check Session Before Clustering
1. Go to **Debug - Session State** page
2. Verify that `adata` exists and shows correct shape
3. If adata is None here, STOP and go back to Step 2A

### 2D. Try Clustering
1. Go to **Clustering & UMAP** page
2. Click **"▶ Run Full Clustering Pipeline"** button
3. **Watch what happens:**
   - ✅ Shows "📊 Processing: X cells × Y genes" → Good
   - ✅ Shows "✅ Data validation passed" → Good
   - ❌ Shows specific error in red box → Copy error message
   - 💥 Page crashes/whites out → Check browser console (F12)

---

## Step 3: What to Tell Me When It Fails

Please provide **exactly**:

1. **Does the "📊 Processing" message appear?**
   - YES → Data is reaching the clustering page
   - NO → Data is being lost somewhere

2. **Does the "✅ Data validation passed" message appear?**
   - YES → adata is valid
   - NO → adata is None or corrupted

3. **What error message appears?** (Copy the exact red error text)

4. **What does the traceback say?** (Click the "Full error traceback" expander)

5. **Browser console errors?** (Right-click → Inspect → Console tab — paste any red errors)

---

## Step 4: If Data is Lost

If adata becomes None between pages:

1. Check **Debug - Session State** after each step
2. Note which page loses the data
3. This will tell us where the bug is

---

## Step 5: Common Causes

| Issue | Fix |
|-------|-----|
| Page shows "adata is None" | Go back to Upload Data and load a dataset |
| QC filtering fails | Check if dataset has mitochondrial gene names (starts with "MT-") |
| Clustering shows "SessionState is None" | Clear browser cache and reload |
| Clustering hangs forever | Kill Streamlit: `pkill -f streamlit` |
| Error about missing column | Dataset columns don't match expected format |

---

## Step 6: Manual Test (Bypass Streamlit)

If Streamlit keeps failing, we can test just the clustering:

```bash
cd /users/simon/python_lessons/scRNA_Explorer
python test_full_workflow.py
```

This runs the exact same code but directly (not through Streamlit).
- If it works here but not in Streamlit → Session state issue
- If it fails everywhere → Pipeline issue

---

## Quick Checklist

- [ ] Streamlit running on port 8501?
- [ ] Can access http://192.168.100.229:8501?
- [ ] Loaded PBMC 3k demo dataset?
- [ ] Ran Quality Control filter?
- [ ] Debug page shows adata exists?
- [ ] Error message shows in clustering page?
- [ ] Copied full error traceback?

---

## Next Steps

1. **Follow Steps 1-3 above carefully**
2. **Tell me:**
   - What error message appears
   - Whether "📊 Processing" message shows
   - Whether "✅ Data validation passed" shows
   - Full traceback from expander
   - Browser console errors (F12)

This will help me identify exactly where the failure is!
