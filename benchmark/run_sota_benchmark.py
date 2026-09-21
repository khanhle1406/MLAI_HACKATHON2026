"""Benchmark Runner for SOTA Data Quality Datasets and VNG Enterprise Data."""

import asyncio
import time
from pathlib import Path
import sys

# Ensure dataguard root is in PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.orchestrator.pipeline import pipeline

DATASETS = [
    ("Hospital (SOTA Benchmark)", "benchmark/datasets/hospital_dirty.csv"),
    ("Flights (SOTA Benchmark)", "benchmark/datasets/flights_dirty.csv"),
    ("Beers (SOTA Benchmark)", "benchmark/datasets/beers_dirty.csv"),
    ("Rayyan (SOTA Benchmark)", "benchmark/datasets/rayyan_dirty.csv"),
    ("Tax - 200,000 rows (SOTA Big Data)", "benchmark/datasets/tax_dirty.csv"),
    ("VNG ZaloPay Transactions - 50,000 rows (VNG FinTech)", "benchmark/datasets/vng_zalopay_transactions.csv"),
]

async def run_benchmark():
    print("=" * 85)
    print(f"{'DATAGUARD BENCHMARK SUITE — SOTA PAPERS & VNG ENTERPRISE':^85}")
    print("=" * 85)
    print(f"{'Dataset':<42} | {'Rows':>8} | {'Cols':>4} | {'AUTO':>6} | {'ESC':>6} | {'Time (s)':>8}")
    print("-" * 85)
    
    total_rows = 0
    total_time = 0.0
    
    for name, rel_path in DATASETS:
        file_path = Path(__file__).resolve().parents[1] / rel_path
        if not file_path.exists():
            print(f"File not found: {file_path}")
            continue
            
        t0 = time.time()
        result = await pipeline.analyze_file(file_path)
        dur = time.time() - t0
        
        summary = result.get("summary", {})
        rep = result.get("assistant_report", {})
        rows = summary.get("total_rows", 0)
        cols = summary.get("total_columns", 0)
        auto_c = summary.get("auto_count", 0)
        esc_c = summary.get("escalate_count", 0)
        domain = rep.get("domain_name", "Unknown")
        entity = rep.get("entity_concept", "Entity")
        
        total_rows += rows
        total_time += dur
        
        print(f"{name:<42} | {rows:>8,d} | {cols:>4} | {auto_c:>6} | {esc_c:>6} | {dur:>7.2f}s")
        print(f"   └─ Đọc hiểu: [{domain[:40]}...] | Thực thể: '{entity}'")
        
    print("=" * 85)
    print(f"TỔNG CỘNG ĐÃ QUÉT: {total_rows:,} dòng trong {total_time:.2f} giây! Tốc độ TB: {int(total_rows/max(total_time, 0.001)):,} dòng/giây.")
    print("=" * 85)

if __name__ == "__main__":
    asyncio.run(run_benchmark())
