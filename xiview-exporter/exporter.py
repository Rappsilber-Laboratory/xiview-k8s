"""
mzidentml-reader module for exporting static xiVIEW network HTML pages and ZIP archives.
"""

import json
import logging
import os
import re
import shutil
import sqlite3
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure python path includes mzidentml-reader for importing parser.DatabaseWriter etc.
if '/home/appuser' not in sys.path:
    sys.path.insert(0, '/home/appuser')

repo_root = Path(__file__).resolve().parent.parent
mz_dir = repo_root / 'mzidentml-reader'
if mz_dir.exists() and str(mz_dir) not in sys.path:
    sys.path.insert(0, str(mz_dir))

logger = logging.getLogger(__name__)


def clean_mzid_file(input_path: str, output_path: str) -> None:
    """
    Remove problematic empty cvParam tags that xiFDR sometimes generates
    (e.g., <cvParam></cvParam> or <cvParam/> with missing attributes)
    which cause pyteomics to raise KeyError: 'name'.
    """
    pattern = re.compile(r'<cvParam\s*(?:/\s*>|>\s*</cvParam>)')
    if input_path.endswith('.gz'):
        import gzip
        with gzip.open(input_path, 'rt', encoding='utf-8') as f_in, open(output_path, 'w', encoding='utf-8') as f_out:
            for line in f_in:
                f_out.write(pattern.sub('', line))
    else:
        with open(input_path, 'r', encoding='utf-8') as f_in, open(output_path, 'w', encoding='utf-8') as f_out:
            for line in f_in:
                f_out.write(pattern.sub('', line))


def parse_mzid_to_sqlite(mzid_path: str, db_path: str, project_name: str) -> None:
    """
    Parse sanitized mzIdentML into SQLite using mzidentml-reader.
    """
    from parser.DatabaseWriter import DatabaseWriter
    from parser.MzIdParser import SqliteMzIdParser
    from parser.database.create_db_schema import create_schema

    if os.path.exists(db_path):
        os.remove(db_path)

    conn_str = f"sqlite:///{os.path.abspath(db_path)}"
    create_schema(conn_str)

    writer = DatabaseWriter(conn_str, upload_id=1, pxid=project_name)
    parser = SqliteMzIdParser(mzid_path, None, writer, logger)
    parser.parse()


def extract_xiview_payloads(db_path: str, blosums_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Extract the 9 xiVIEW dataset endpoints from the parsed SQLite database.
    """
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    # 1. mzidentml_files
    mz_files: List[Dict[str, Any]] = []
    for row in cur.execute("""
        SELECT id, project_id, identification_file_name, analysis_software_list,
               provider, audit_collection, analysis_sample_collection, bib, spectra_formats
        FROM upload
    """):
        d = dict(row)
        for k in ['analysis_software_list', 'provider', 'audit_collection', 'analysis_sample_collection', 'bib', 'spectra_formats']:
            if isinstance(d.get(k), str):
                try:
                    d[k] = json.loads(d[k])
                except Exception:
                    pass
        mz_files.append(d)

    # 2. analysis_collection_spectrum_identifications
    ac_data: List[Dict[str, Any]] = []
    for row in cur.execute("""
        SELECT upload_id, spectrum_identification_list_ref, spectrum_identification_protocol_ref,
               spectra_data_refs, search_database_refs
        FROM analysiscollectionspectrumidentification
    """):
        d = dict(row)
        for k in ['spectra_data_refs', 'search_database_refs']:
            if isinstance(d.get(k), str):
                try:
                    d[k] = json.loads(d[k])
                except Exception:
                    pass
        ac_data.append(d)

    # 3. spectrum_identification_protocols
    sip_data: List[Dict[str, Any]] = []
    for row in cur.execute("""
        SELECT id, sip_ref, upload_id, frag_tol, frag_tol_unit, additional_search_params, analysis_software, threshold
        FROM spectrumidentificationprotocol
    """):
        d = dict(row)
        for k in ['additional_search_params', 'analysis_software', 'threshold']:
            if isinstance(d.get(k), str):
                try:
                    d[k] = json.loads(d[k])
                except Exception:
                    pass
        sip_data.append(d)

    # 4. spectra_data
    sd_data = [dict(row) for row in cur.execute("SELECT * FROM spectradata")]

    # 5. enzymes
    enz_data: List[Dict[str, Any]] = []
    for row in cur.execute("SELECT * FROM enzyme"):
        d = dict(row)
        for k in d:
            if isinstance(d[k], str) and (d[k].startswith('{') or d[k].startswith('[')):
                try:
                    d[k] = json.loads(d[k])
                except Exception:
                    pass
        enz_data.append(d)

    # 6. search_modifications
    sm_data: List[Dict[str, Any]] = []
    for row in cur.execute("SELECT * FROM searchmodification"):
        d = dict(row)
        for k in d:
            if isinstance(d[k], str) and (d[k].startswith('{') or d[k].startswith('[')):
                try:
                    d[k] = json.loads(d[k])
                except Exception:
                    pass
        sm_data.append(d)

    # 7. matches (filtered for pass_threshold = 1 and link_site1 > -1)
    matches_data: List[Dict[str, Any]] = []
    for row in cur.execute("""
        SELECT si.id AS id, si.pep1_id AS pi1, si.pep2_id AS pi2,
           si.scores AS sc,
           si.upload_id AS ui,
           si.calc_mz AS c_mz,
           si.charge_state AS pc_c,
           si.exp_mz AS pc_mz,
           si.spectrum_id AS sp,
           si.spectra_data_id AS sd,
           si.pass_threshold AS p,
           si.rank AS r,
           si.sip_id AS sip,
           si.multiple_spectra_identification_id AS msi_id,
           si.multiple_spectra_identification_pc AS msi_pc
        FROM match si
        INNER JOIN modifiedpeptide mp1 ON si.upload_id = mp1.upload_id AND si.pep1_id = mp1.id
        LEFT JOIN modifiedpeptide mp2 ON si.upload_id = mp2.upload_id AND si.pep2_id = mp2.id
        WHERE si.pass_threshold = 1
        AND mp1.link_site1 > -1
    """):
        d = dict(row)
        if isinstance(d.get('sc'), str):
            try:
                d['sc'] = json.loads(d['sc'])
            except Exception:
                pass
        d['p'] = bool(d['p'])
        matches_data.append(d)

    # 8. peptides (joined with peptideevidence)
    cur.execute("""
        SELECT DISTINCT pep1_id FROM match WHERE pass_threshold = 1
        UNION
        SELECT DISTINCT pep2_id FROM match WHERE pass_threshold = 1 AND pep2_id IS NOT NULL
    """)
    pep_ids = set(r[0] for r in cur.fetchall())

    pep_evs: Dict[int, Dict[str, List[Any]]] = {}
    for row in cur.execute("SELECT peptide_id, dbsequence_id, pep_start, is_decoy FROM peptideevidence"):
        pid = row['peptide_id']
        if pid not in pep_evs:
            pep_evs[pid] = {'prt': [], 'pos': [], 'dec': []}
        pep_evs[pid]['prt'].append(row['dbsequence_id'])
        pep_evs[pid]['pos'].append(row['pep_start'])
        pep_evs[pid]['dec'].append(bool(row['is_decoy']))

    peptides_data: List[Dict[str, Any]] = []
    for row in cur.execute("""
        SELECT id, upload_id AS u_id, base_sequence AS seq,
               link_site1 AS ls1, link_site2 AS ls2,
               mod_accessions AS m_as, mod_positions AS m_ps,
               mod_monoiso_mass_deltas AS m_ms, crosslinker_modmass AS cl_m
        FROM modifiedpeptide
    """):
        pid = row['id']
        if pid not in pep_ids or pid not in pep_evs:
            continue
        d = dict(row)
        d['prt'] = pep_evs[pid]['prt']
        d['pos'] = pep_evs[pid]['pos']
        d['dec'] = pep_evs[pid]['dec']
        for k in ['m_as', 'm_ps', 'm_ms']:
            if isinstance(d.get(k), str):
                try:
                    d[k] = json.loads(d[k])
                except Exception:
                    pass
        peptides_data.append(d)

    # 9. proteins
    proteins_data: List[Dict[str, Any]] = []
    for row in cur.execute("""
        SELECT id, name, accession, sequence,
               cast(upload_id as text) AS search_id, description
        FROM dbsequence
    """):
        proteins_data.append(dict(row))

    con.close()

    # Load blosums matrix
    blosums_data = {}
    if blosums_path and os.path.exists(blosums_path):
        with open(blosums_path, "r", encoding="utf-8") as f:
            blosums_data = json.load(f)

    return {
        "get_xiview_mzidentml_files": mz_files,
        "get_xiview_analysis_collection_spectrum_identifications": ac_data,
        "get_xiview_spectrum_identification_protocols": sip_data,
        "get_xiview_spectra_data": sd_data,
        "get_xiview_enzymes": enz_data,
        "get_xiview_search_modifications": sm_data,
        "get_xiview_matches": matches_data,
        "get_xiview_peptides": peptides_data,
        "get_xiview_proteins": proteins_data,
        "blosums": blosums_data,
    }


def generate_default_layout(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generates a clean default layout positioning all proteins in the dataset.
    """
    import math
    proteins = payload.get("get_xiview_proteins", [])
    prot_list = []
    n = len(proteins)
    cx, cy = 500.0, 400.0
    radius = min(450.0, max(180.0, n * 14.0))
    for i, p in enumerate(proteins):
        angle = (2 * math.pi * i) / max(1, n)
        px = cx + radius * math.cos(angle)
        py = cy + radius * math.sin(angle)
        prot_list.append({
            "id": p["id"],
            "name": p.get("name", p["id"]),
            "x": round(px, 1),
            "y": round(py, 1),
            "rot": 0,
            "stickZoom": 1,
            "expanded": False,
            "flipped": False,
            "manuallyHidden": False
        })
    return {
        "proteins": prot_list,
        "groups": []
    }


def generate_static_package(
    payload: Dict[str, Any],
    static_assets_dir: str,
    output_dir: str,
    title: str = "xiVIEW Crosslink Network",
    structure_paths: Optional[List[str]] = None,
    auto_load_structure: bool = False,
    layout_path: Optional[str] = None,
    layout_data: Optional[Dict[str, Any]] = None
) -> str:
    """
    Build the standalone static directory with HTML, assets, and offline data shim.
    """
    os.makedirs(output_dir, exist_ok=True)

    excluded = {"network.html", "xidocs", "go.obo", ".git", "__pycache__"}
    for item in os.listdir(static_assets_dir):
        if item in excluded:
            continue
        src = os.path.join(static_assets_dir, item)
        dst = os.path.join(output_dir, item)
        if os.path.isdir(src):
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)

    out_xiview_js = os.path.join(output_dir, "xiview.js")
    if os.path.exists(out_xiview_js):
        try:
            with open(out_xiview_js, "r", encoding="utf-8") as f:
                js_code = f.read()
            old_vent = 'const ut={};D.extend(ut,F().Events);const pt=ut;'
            new_vent = 'const ut={};D.extend(ut,F().Events);const pt=ut;window.__xiview_vent=pt;'
            if old_vent in js_code and 'window.__xiview_vent' not in js_code:
                with open(out_xiview_js, "w", encoding="utf-8") as f:
                    f.write(js_code.replace(old_vent, new_vent))
        except Exception as e:
            logger.warning("Could not patch xiview.js event bus: %s", e)

    # Patch pride.css to unhide layout controls
    out_pride_css = os.path.join(output_dir, "pride.css")
    if os.path.exists(out_pride_css):
        try:
            with open(out_pride_css, "r", encoding="utf-8") as f:
                css_code = f.read()
            css_code = css_code.replace(
                "#loadLayoutButton {\n    display: none !important;\n}",
                "#loadLayoutButton {\n    display: inline-block !important;\n}"
            ).replace(
                ".savedLayoutName {\n    display: none !important;\n}",
                ".savedLayoutName {\n    display: inline-block !important;\n}"
            ).replace(
                ".saveLayoutButton {\n    display: none !important;\n}",
                ".saveLayoutButton {\n    display: inline-block !important;\n}"
            )
            with open(out_pride_css, "w", encoding="utf-8") as f:
                f.write(css_code)
        except Exception as e:
            logger.warning("Could not patch pride.css layout button rules: %s", e)

    # Bundle 3D structure files if provided
    payload["structures"] = {}
    payload["auto_load_structure"] = auto_load_structure
    if structure_paths:
        struct_dir = os.path.join(output_dir, "structures")
        os.makedirs(struct_dir, exist_ok=True)
        for sp in structure_paths:
            if os.path.isfile(sp):
                fname = os.path.basename(sp)
                shutil.copy2(sp, os.path.join(struct_dir, fname))
                try:
                    with open(sp, "r", encoding="utf-8", errors="replace") as sf:
                        payload["structures"][fname] = sf.read()
                    logger.info("Bundled 3D structure: %s (%d bytes)", fname, len(payload["structures"][fname]))
                except Exception as e:
                    logger.warning("Failed to read structure file %s: %s", sp, e)

    # Bundle layout (protein coordinates and groupings) if provided
    loaded_layout = None
    if layout_data:
        loaded_layout = layout_data
    elif layout_path and os.path.isfile(layout_path):
        try:
            with open(layout_path, "r", encoding="utf-8") as lf:
                loaded_layout = json.load(lf)
            logger.info("Loaded layout from file: %s", layout_path)
        except Exception as e:
            logger.warning("Failed to load layout from %s: %s", layout_path, e)

    payload["layout"] = loaded_layout
    if loaded_layout:
        layout_dir = os.path.join(output_dir, "layouts")
        os.makedirs(layout_dir, exist_ok=True)
        with open(os.path.join(layout_dir, "default_layout.json"), "w", encoding="utf-8") as lf:
            json.dump(loaded_layout, lf, indent=2)

    data_js_path = os.path.join(output_dir, "data.js")
    with open(data_js_path, "w", encoding="utf-8") as f:
        f.write("window.__XIVIEW_DATA__ = " + json.dumps(payload) + ";\n")

    network_template_path = os.path.join(static_assets_dir, "network.html")
    with open(network_template_path, "r", encoding="utf-8") as f:
        html = f.read()

    pre_loader_shim = """        <script type="text/javascript" src="./data.js"></script>
        <script>
        // Offline Shim: intercept fetch and Backbone before vendor scripts load
        (function() {
            const offlineData = window.__XIVIEW_DATA__ || {};

            const originalFetch = window.fetch;
            window.fetch = function(url, options) {
                const urlStr = typeof url === 'string' ? url : (url.url || '');
                const lower = urlStr.toLowerCase();

                // Check bundled 3D structures first
                if (offlineData.structures) {
                    for (const [sName, sContent] of Object.entries(offlineData.structures)) {
                        const sLower = sName.toLowerCase();
                        if (lower.endsWith(sLower) || lower.includes('/' + sLower) || lower === sLower) {
                            return Promise.resolve(new Response(sContent, {
                                status: 200,
                                headers: { 'Content-Type': 'text/plain' }
                            }));
                        }
                    }
                }

                let targetKey = null;
                for (const key of Object.keys(offlineData)) {
                    if (lower.includes(key.toLowerCase()) || key.toLowerCase().includes(lower.split('/').pop())) {
                        targetKey = key;
                        break;
                    }
                }
                if (!targetKey) {
                    if (lower.includes('upload') || lower.includes('mzidentml')) targetKey = 'get_xiview_mzidentml_files';
                    else if (lower.includes('ac') || lower.includes('analysis_collection')) targetKey = 'get_xiview_analysis_collection_spectrum_identifications';
                    else if (lower.includes('sip') || lower.includes('protocol')) targetKey = 'get_xiview_spectrum_identification_protocols';
                    else if (lower.includes('spectra') || lower.includes('spectradata')) targetKey = 'get_xiview_spectra_data';
                    else if (lower.includes('enzyme')) targetKey = 'get_xiview_enzymes';
                    else if (lower.includes('modification')) targetKey = 'get_xiview_search_modifications';
                    else if (lower.includes('match')) targetKey = 'get_xiview_matches';
                    else if (lower.includes('peptide')) targetKey = 'get_xiview_peptides';
                    else if (lower.includes('protein') || lower.includes('dbsequence')) targetKey = 'get_xiview_proteins';
                    else if (lower.includes('blosum')) targetKey = 'blosums';
                }
                const data = targetKey ? offlineData[targetKey] : null;
                if (data) {
                    return Promise.resolve(new Response(JSON.stringify(data), {
                        status: 200,
                        headers: { 'Content-Type': 'application/json' }
                    }));
                }
                return originalFetch ? originalFetch.apply(this, arguments) : Promise.reject(new Error("Offline viewer: request intercepted for " + urlStr));
            };

            let _Backbone = window.Backbone;
            function patchBackbone(bb) {
                if (bb && bb.ajax && !bb.ajax._isPatched) {
                    const origAjax = bb.ajax;
                    bb.ajax = function(method, model, options) {
                        const opts = options || (typeof method === 'object' ? method : {});
                        const url = opts.url || (model && model.url) || (typeof method === 'string' ? method : '');
                        const lower = url.toLowerCase();
                        let targetKey = null;
                        for (const key of Object.keys(offlineData)) {
                            if (lower.includes(key.toLowerCase()) || key.toLowerCase().includes(lower.split('/').pop())) {
                                targetKey = key;
                                break;
                            }
                        }
                        if (!targetKey) {
                            if (lower.includes('blosum')) targetKey = 'blosums';
                        }
                        const data = targetKey ? offlineData[targetKey] : null;
                        if (data) {
                            if (typeof opts.success === 'function') {
                                opts.success(data, "success", {});
                            }
                            return {
                                then: function(cb) { cb(data); return this; },
                                done: function(cb) { cb(data); return this; },
                                fail: function() { return this; },
                                always: function(cb) { cb(); return this; }
                            };
                        }
                        return origAjax.apply(this, arguments);
                    };
                    bb.ajax._isPatched = true;
                }
            }

            if (window.Backbone) {
                patchBackbone(window.Backbone);
            } else {
                Object.defineProperty(window, 'Backbone', {
                    configurable: true,
                    enumerable: true,
                    get: function() { return _Backbone; },
                    set: function(val) {
                        _Backbone = val;
                        patchBackbone(_Backbone);
                    }
                });
            }

            // 3D Structure Viewer and WebGL Diagnostic Enhancements
            function isWebGLSupported() {
                try {
                    const c = document.createElement('canvas');
                    return !!(window.WebGLRenderingContext && (c.getContext('webgl') || c.getContext('experimental-webgl')));
                } catch(e) {
                    return false;
                }
            }

            window.__loadBundledStructure = function(name) {
                const content = (offlineData.structures || {})[name];
                if (!content) {
                    console.error("Structure not found in bundled data:", name);
                    return;
                }
                const input = document.querySelector('#pdbPanel .selectPdbButton');
                if (!input) {
                    console.error("selectPdbButton not found in #pdbPanel");
                    return;
                }
                try {
                    const file = new File([content], name, { type: 'application/text' });
                    const dt = new DataTransfer();
                    dt.items.add(file);
                    input.files = dt.files;
                    input.dispatchEvent(new Event('change', { bubbles: true }));
                    console.log("Dispatched bundled structure load for:", name);
                } catch(err) {
                    console.error("Failed to dispatch bundled structure load:", err);
                }
            };

            function setup3DViewerUI() {
                const pdbPanel = document.querySelector('#pdbPanel .columnbar');
                if (!pdbPanel || pdbPanel._hasOfflineUI) return;
                pdbPanel._hasOfflineUI = true;

                // WebGL Diagnostic Notice if WebGL is unavailable (e.g. over RDP / Remote Desktop)
                if (!isWebGLSupported()) {
                    const alertBox = document.createElement('div');
                    alertBox.className = 'webgl-rdp-warning';
                    alertBox.style.cssText = 'background: #fff3cd; color: #856404; border: 1px solid #ffeeba; padding: 10px; margin: 10px 0; border-radius: 4px; font-size: 13px; line-height: 1.4;';
                    alertBox.innerHTML = '<strong>⚠️ WebGL Acceleration Unavailable:</strong><br>' +
                        'Hardware WebGL is disabled by your display server (common over RDP / Remote Desktop).<br>' +
                        'To enable CPU SwiftShader WebGL in Chrome, restart Chrome with:<br>' +
                        '<code style=\"display:block; background:#f8f9fa; padding:4px 6px; margin:6px 0; border:1px solid #ddd; font-family:monospace; color:#333;\">google-chrome --enable-unsafe-swiftshader --ignore-gpu-blocklist</code>' +
                        'or enable <em>Override software rendering list</em> in <code>chrome://flags</code>.';
                    pdbPanel.prepend(alertBox);
                }

                // Bundled 3D structures 1-click loading buttons
                const structures = offlineData.structures || {};
                const sNames = Object.keys(structures);
                if (sNames.length > 0) {
                    const section = document.createElement('div');
                    section.className = 'bundled-structures-section';
                    section.style.cssText = 'margin-bottom: 15px; padding-bottom: 12px; border-bottom: 1px solid #e0e0e0;';

                    const heading = document.createElement('p');
                    heading.className = 'smallHeading';
                    heading.style.fontWeight = 'bold';
                    heading.textContent = 'Bundled 3D Model' + (sNames.length > 1 ? 's' : '');
                    section.appendChild(heading);

                    sNames.forEach(function(sName) {
                        const btn = document.createElement('button');
                        btn.className = 'btn btn-1 btn-1a bundled-struct-btn';
                        btn.style.cssText = 'display: inline-block; margin: 4px 6px 4px 0; padding: 6px 14px; font-weight: bold; background: #2c7bb6; color: white; border: none; border-radius: 4px; cursor: pointer;';
                        btn.innerHTML = '<i class=\"fa fa-cube\" style=\"margin-right:6px;\"></i>Load ' + sName;
                        btn.onclick = function(e) {
                            e.preventDefault();
                            window.__loadBundledStructure(sName);
                        };
                        section.appendChild(btn);
                    });

                    pdbPanel.insertBefore(section, pdbPanel.firstChild);
                }
            }

            // Inject styling to unhide and style layout management buttons
            const layoutStyle = document.createElement('style');
            layoutStyle.textContent = `
                #loadLayoutButton, .savedLayoutName, .saveLayoutButton {
                    display: inline-block !important;
                    vertical-align: middle !important;
                }
                #loadLayoutButton {
                    cursor: pointer !important;
                    margin-right: 6px !important;
                    background-color: #f7fafc !important;
                    border: 1px solid #cbd5e1 !important;
                    padding: 3px 10px !important;
                    border-radius: 4px !important;
                    font-size: 12px !important;
                    color: #1e293b !important;
                    text-transform: none !important;
                }
                #loadLayoutButton:hover {
                    background-color: #e2e8f0 !important;
                    border-color: #94a3b8 !important;
                }
                .saveLayoutButton {
                    cursor: pointer !important;
                    margin-left: 4px !important;
                    background-color: #f7fafc !important;
                    border: 1px solid #cbd5e1 !important;
                    padding: 3px 10px !important;
                    border-radius: 4px !important;
                    font-size: 12px !important;
                    color: #1e293b !important;
                }
                .saveLayoutButton:hover {
                    background-color: #e2e8f0 !important;
                    border-color: #94a3b8 !important;
                }
                .savedLayoutName {
                    padding: 3px 8px !important;
                    border: 1px solid #cbd5e1 !important;
                    border-radius: 4px !important;
                    font-size: 12px !important;
                    width: 140px !important;
                }
            `;
            document.head.appendChild(layoutStyle);

            // ID Normalization so accessions, names, or dbseq_ IDs all map correctly
            function normalizeLayout(layoutObj) {
                if (!layoutObj) return layoutObj;
                const proteins = offlineData.get_xiview_proteins || [];
                const idMap = new Map();
                proteins.forEach(function(p) {
                    if (p.id) idMap.set(p.id, p.id);
                    if (p.accession) idMap.set(p.accession, p.id);
                    if (p.name) idMap.set(p.name, p.id);
                    if (p.id && p.id.startsWith('dbseq_')) {
                        idMap.set(p.id.replace('dbseq_', ''), p.id);
                    }
                });

                const norm = JSON.parse(JSON.stringify(layoutObj));
                if (Array.isArray(norm.proteins)) {
                    norm.proteins.forEach(function(p) {
                        if (idMap.has(p.id)) p.id = idMap.get(p.id);
                        else if (idMap.has('dbseq_' + p.id)) p.id = idMap.get('dbseq_' + p.id);
                    });
                }
                if (Array.isArray(norm.groups)) {
                    norm.groups.forEach(function(g) {
                        if (Array.isArray(g.proteinIds)) {
                            g.proteinIds = g.proteinIds.map(function(pid) {
                                if (idMap.has(pid)) return idMap.get(pid);
                                if (idMap.has('dbseq_' + pid)) return idMap.get('dbseq_' + pid);
                                return pid;
                            });
                        }
                    });
                }
                return norm;
            }

            function getXiNetController() {
                if (window.__xinet) return window.__xinet;
                if (!window.__xiview_vent || !window.__xiview_vent._events || !window.__xiview_vent._events.xinetLoadLayout) {
                    return null;
                }
                const listeners = window.__xiview_vent._events.xinetLoadLayout;
                if (Array.isArray(listeners)) {
                    for (const l of listeners) {
                        const ctx = l.context || l.ctx;
                        if (ctx && ctx.renderedProteins) return ctx;
                    }
                } else if (listeners && (listeners.context || listeners.ctx)) {
                    return listeners.context || listeners.ctx;
                }
                return null;
            }

            function loadLayoutIntoNetwork(layoutObj) {
                if (!layoutObj) return;
                const ctrl = getXiNetController();
                if (ctrl) {
                    ctrl.firstRender = false;
                    if (ctrl.d3cola) {
                        try { ctrl.d3cola.stop(); } catch(e) {}
                    }
                    if (ctrl.renderedProteins) {
                        for (const p of ctrl.renderedProteins.values()) {
                            p.fixed = true;
                        }
                    }
                }
                const norm = normalizeLayout(layoutObj);
                console.log("Loading layout into xiNET:", norm);
                if (window.__xiview_vent) {
                    window.__xiview_vent.trigger('xinetLoadLayout', norm);
                }
                if (ctrl && ctrl.d3cola) {
                    try { ctrl.d3cola.stop(); } catch(e) {}
                }
            }

            // Layout Management & Grouping Persistence
            function setupLayoutControls() {
                const saveBtn = document.querySelector('.saveLayoutButton');
                const nameInput = document.querySelector('.savedLayoutName');
                const loadBtn = document.getElementById('loadLayoutButton');

                if (saveBtn) {
                    saveBtn.style.setProperty('display', 'inline-block', 'important');
                    saveBtn.style.cursor = 'pointer';
                    if (!saveBtn._hasLayoutHandler) {
                        saveBtn._hasLayoutHandler = true;
                        saveBtn.addEventListener('click', function(e) {
                            e.preventDefault();
                            e.stopPropagation();
                            if (!window.__xiview_vent) return;
                            const layoutName = (nameInput && nameInput.value.trim()) || ('Layout_' + new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-'));
                            window.__xiview_vent.trigger('xinetSaveLayout', function(layoutStr) {
                                try {
                                    const layoutObj = JSON.parse(layoutStr);
                                    // Save in localStorage
                                    const storageKey = 'xiview_layouts_' + (document.title || 'dataset');
                                    const existing = JSON.parse(localStorage.getItem(storageKey) || '{}');
                                    existing[layoutName] = layoutObj;
                                    localStorage.setItem(storageKey, JSON.stringify(existing));

                                    // Also trigger file download of layout JSON
                                    const blob = new Blob([JSON.stringify(layoutObj, null, 2)], { type: 'application/json' });
                                    const a = document.createElement('a');
                                    a.href = URL.createObjectURL(blob);
                                    a.download = layoutName + '.layout.json';
                                    document.body.appendChild(a);
                                    a.click();
                                    URL.revokeObjectURL(a.href);
                                    a.remove();

                                    alert('Layout "' + layoutName + '" successfully saved and downloaded as JSON!');
                                } catch(err) {
                                    console.error('Failed to save layout:', err);
                                }
                            });
                        });
                    }
                }

                if (nameInput) {
                    nameInput.style.setProperty('display', 'inline-block', 'important');
                }

                if (loadBtn) {
                    loadBtn.style.setProperty('display', 'inline-block', 'important');
                    loadBtn.style.cursor = 'pointer';
                    if (!loadBtn._hasLayoutHandler) {
                        loadBtn._hasLayoutHandler = true;
                        loadBtn.textContent = 'Load Layout ▼';

                        // Hidden file input for importing layout JSON
                        let fileInput = document.getElementById('hiddenLayoutFileInput');
                        if (!fileInput) {
                            fileInput = document.createElement('input');
                            fileInput.type = 'file';
                            fileInput.id = 'hiddenLayoutFileInput';
                            fileInput.accept = '.json';
                            fileInput.style.display = 'none';
                            fileInput.addEventListener('change', function(e) {
                                const file = e.target.files && e.target.files[0];
                                if (!file) return;
                                const reader = new FileReader();
                                reader.onload = function(evt) {
                                    try {
                                        const parsed = JSON.parse(evt.target.result);
                                        loadLayoutIntoNetwork(parsed);
                                        alert('Successfully loaded layout from ' + file.name);
                                    } catch(err) {
                                        alert('Failed to parse layout file: ' + err.message);
                                    }
                                };
                                reader.readAsText(file);
                                e.target.value = null;
                            });
                            document.body.appendChild(fileInput);
                        }

                        loadBtn.addEventListener('click', function(e) {
                            e.preventDefault();
                            e.stopPropagation();

                            // Build dropdown menu
                            let menu = document.getElementById('layoutDropdownMenu');
                            if (menu) {
                                menu.remove();
                                return;
                            }
                            menu = document.createElement('div');
                            menu.id = 'layoutDropdownMenu';
                            menu.style.cssText = 'position: absolute; background: white; border: 1px solid #ccc; box-shadow: 0 4px 12px rgba(0,0,0,0.15); border-radius: 4px; z-index: 10000; min-width: 220px; font-family: sans-serif; font-size: 13px; color: #333; padding: 6px 0;';

                            const rect = loadBtn.getBoundingClientRect();
                            menu.style.top = (rect.bottom + window.scrollY + 4) + 'px';
                            menu.style.left = (rect.left + window.scrollX) + 'px';

                            const addItem = (label, icon, onClick) => {
                                const item = document.createElement('div');
                                item.style.cssText = 'padding: 8px 14px; cursor: pointer; display: flex; align-items: center; gap: 8px;';
                                item.innerHTML = (icon ? '<i class="fa ' + icon + '"></i> ' : '') + label;
                                item.onmouseover = () => item.style.background = '#f0f4f8';
                                item.onmouseout = () => item.style.background = 'white';
                                item.onclick = (evt) => {
                                    menu.remove();
                                    onClick(evt);
                                };
                                menu.appendChild(item);
                            };

                            if (offlineData.layout) {
                                addItem('Default Layout (Bundled)', 'fa-star', () => {
                                    loadLayoutIntoNetwork(offlineData.layout);
                                });
                            }

                            // LocalStorage layouts
                            const storageKey = 'xiview_layouts_' + (document.title || 'dataset');
                            const saved = JSON.parse(localStorage.getItem(storageKey) || '{}');
                            const sNames = Object.keys(saved);
                            if (sNames.length > 0) {
                                const div = document.createElement('div');
                                div.style.cssText = 'border-top: 1px solid #eee; margin: 4px 0; padding: 4px 14px; font-size: 11px; font-weight: bold; color: #888; text-transform: uppercase;';
                                div.textContent = 'Saved in Browser';
                                menu.appendChild(div);
                                sNames.forEach(n => {
                                    addItem(n, 'fa-bookmark', () => {
                                        loadLayoutIntoNetwork(saved[n]);
                                    });
                                });
                            }

                            const div2 = document.createElement('div');
                            div2.style.cssText = 'border-top: 1px solid #eee; margin: 4px 0;';
                            menu.appendChild(div2);

                            addItem('Import Layout JSON File...', 'fa-folder-open', () => {
                                fileInput.click();
                            });

                            document.body.appendChild(menu);
                            const closeOnClickAway = function(evt) {
                                if (!menu.contains(evt.target) && evt.target !== loadBtn) {
                                    menu.remove();
                                    document.removeEventListener('click', closeOnClickAway);
                                }
                            };
                            setTimeout(() => document.addEventListener('click', closeOnClickAway), 50);
                        });
                    }
                }
            }

            let hasAppliedDefaultLayout = false;
            function applyDefaultLayout() {
                if (hasAppliedDefaultLayout || !offlineData.layout) return;
                console.log("Applying default bundled layout with groupings...");
                let attempts = 0;
                const readyTimer = setInterval(() => {
                    attempts++;
                    const ctrl = getXiNetController();
                    if (ctrl && ctrl.renderedProteins && ctrl.renderedProteins.size > 0) {
                        clearInterval(readyTimer);
                        if (!hasAppliedDefaultLayout) {
                            hasAppliedDefaultLayout = true;
                            ctrl.firstRender = false;
                            if (ctrl.d3cola) {
                                try { ctrl.d3cola.stop(); } catch(e) {}
                            }
                            loadLayoutIntoNetwork(offlineData.layout);
                        }
                    } else if (attempts > 150) {
                        clearInterval(readyTimer);
                    }
                }, 200);
            }

            function hookVentEvents() {
                if (window.__xiview_vent && !window.__xiview_vent._hasLayoutHook) {
                    window.__xiview_vent._hasLayoutHook = true;
                    window.__xiview_vent.on('initialSetupDone', function() {
                        console.log("xiVIEW initialSetupDone triggered");
                        setupLayoutControls();
                        applyDefaultLayout();
                    });
                }
            }

            window.addEventListener('DOMContentLoaded', function() {
                const pdbBtn = document.getElementById('pdbLoadButton');
                if (pdbBtn) {
                    pdbBtn.addEventListener('click', function() {
                        setTimeout(setup3DViewerUI, 100);
                    });
                }
                setTimeout(setup3DViewerUI, 1200);
                setTimeout(setupLayoutControls, 800);
                setTimeout(hookVentEvents, 200);

                // Auto-apply layout after xiVIEW network finishes initial render
                setTimeout(applyDefaultLayout, 2200);

                // Periodic check for dynamically re-rendered button bar
                setInterval(setupLayoutControls, 1000);
                setInterval(hookVentEvents, 1000);

                if (offlineData.auto_load_structure && offlineData.structures) {
                    const sList = Object.keys(offlineData.structures);
                    if (sList.length > 0) {
                        setTimeout(function() {
                            setup3DViewerUI();
                            window.__loadBundledStructure(sList[0]);
                        }, 2500);
                    }
                }
            });
        })();
        </script>
        <script type="text/javascript" src="./vendors.js"></script>"""

    html = html.replace(
        '<script type="text/javascript" src="./vendors.js"></script>',
        pre_loader_shim
    )

    html = re.sub(r'<title>.*?</title>', f'<title>{title}</title>', html)

    main_launcher = f"""
    <script>
    //<![CDATA[
    document.title = {json.dumps(title)};
    xiview.main("static_data/", "static_xiAnnotator/");
    //]]>
    </script>
"""

    html = re.sub(
        r'<script>\s*//<!\[CDATA\[\s*xiview\.main\([^\)]+\);\s*(?://[^\n]*\s*)*//\]\]>\s*</script>',
        main_launcher,
        html
    )

    index_html_path = os.path.join(output_dir, "index.html")
    with open(index_html_path, "w", encoding="utf-8") as f:
        f.write(html)

    return output_dir


def create_zip_archive(source_dir: str, zip_path: str) -> str:
    """
    Compress the static package directory into a portable ZIP archive.
    """
    zip_abs = os.path.abspath(zip_path)
    os.makedirs(os.path.dirname(zip_abs), exist_ok=True)
    if os.path.exists(zip_abs):
        os.remove(zip_abs)

    with zipfile.ZipFile(zip_abs, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, source_dir)
                zf.write(full_path, rel_path)

    return zip_abs


def export_static_xiview(
    mzid_path: str,
    output_zip: str,
    project_title: Optional[str] = None,
    static_assets_dir: Optional[str] = None,
    structure_paths: Optional[List[str]] = None,
    auto_load_structure: bool = False,
    layout_path: Optional[str] = None,
    layout_data: Optional[Dict[str, Any]] = None
) -> str:
    """
    End-to-end pipeline to convert an mzIdentML file into a standalone static xiVIEW ZIP.
    """
    if not static_assets_dir:
        candidates = [
            Path("/home/default/workspaces/misc/xiview-k8s/xiview-server/static"),
            Path(__file__).parent.parent.parent / "xiview-server" / "static",
            Path("/home/appuser/static")
        ]
        for c in candidates:
            if c.exists() and (c / "network.html").exists():
                static_assets_dir = str(c)
                break

    if not static_assets_dir or not os.path.exists(static_assets_dir):
        raise FileNotFoundError(f"Could not locate xiview-server/static assets at {static_assets_dir}")

    blosums_path = os.path.join(static_assets_dir, "R", "blosums.json")
    base_name = os.path.basename(mzid_path)
    clean_name = os.path.splitext(os.path.splitext(base_name)[0])[0]
    if not project_title:
        project_title = f"xiVIEW - {clean_name}"

    with tempfile.TemporaryDirectory() as tmp_dir:
        cleaned_mzid = os.path.join(tmp_dir, "sanitized.mzid")
        clean_mzid_file(mzid_path, cleaned_mzid)

        db_path = os.path.join(tmp_dir, "dataset.db")
        parse_mzid_to_sqlite(cleaned_mzid, db_path, project_name=clean_name)

        payload = extract_xiview_payloads(db_path, blosums_path=blosums_path)

        staging_dir = os.path.join(tmp_dir, "xiview_static_site")
        generate_static_package(
            payload=payload,
            static_assets_dir=static_assets_dir,
            output_dir=staging_dir,
            title=project_title,
            structure_paths=structure_paths,
            auto_load_structure=auto_load_structure,
            layout_path=layout_path,
            layout_data=layout_data
        )

        final_zip = create_zip_archive(staging_dir, output_zip)

    return final_zip


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Export standalone static xiVIEW HTML package as a ZIP archive")
    parser.add_argument("-i", "--input", required=True, help="Input mzIdentML file (.mzid or .mzid.gz)")
    parser.add_argument("-o", "--output", help="Output ZIP file (default: <base_name>_static_xiview.zip)")
    parser.add_argument("-s", "--structures", nargs="*", help="Optional structure files (.cif, .pdb)")
    parser.add_argument("-l", "--layout", help="Optional saved layout JSON file")
    parser.add_argument("-t", "--title", help="Optional project title for the visualization")
    args = parser.parse_args()

    out_zip = args.output
    if not out_zip:
        bname = os.path.splitext(os.path.basename(args.input))[0]
        if bname.endswith('.mzid'):
            bname = os.path.splitext(bname)[0]
        out_zip = f"{bname}_static_xiview.zip"

    print(f"Exporting static xiVIEW package for: {args.input}")
    res = export_static_xiview(
        mzid_path=args.input,
        output_zip=out_zip,
        project_title=args.title,
        structure_paths=args.structures,
        layout_path=args.layout
    )
    print(f"Export completed: {res}")

