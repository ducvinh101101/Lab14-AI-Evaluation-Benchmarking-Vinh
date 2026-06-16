import asyncio
import json
import os
import time
import sys
from engine.runner import BenchmarkRunner
from agent.main_agent import MainAgent
from engine.retrieval_eval import RetrievalEvaluator
from engine.llm_judge import LLMJudge

# Reconfigure stdout/stderr to utf-8 for Windows compatibility
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

async def run_benchmark_with_results(agent_version: str):
    print(f"🚀 Khởi động Benchmark cho phiên bản: {agent_version}...")

    if not os.path.exists("data/golden_set.jsonl"):
        print("❌ Thiếu data/golden_set.jsonl. Hãy chạy 'python data/synthetic_gen.py' trước.")
        return None, None

    with open("data/golden_set.jsonl", "r", encoding="utf-8") as f:
        dataset = [json.loads(line) for line in f if line.strip()]

    if not dataset:
        print("❌ File data/golden_set.jsonl rỗng. Hãy tạo ít nhất 1 test case.")
        return None, None

    # Khởi tạo Agent và các bộ đánh giá thực tế
    agent = MainAgent(version=agent_version)
    evaluator = RetrievalEvaluator()
    judge = LLMJudge()
    
    runner = BenchmarkRunner(agent, evaluator, judge)
    results = await runner.run_all(dataset, batch_size=5)

    total = len(results)
    
    avg_score = sum(r["judge"]["final_score"] for r in results) / total
    hit_rate = sum(r["ragas"]["retrieval"]["hit_rate"] for r in results) / total
    agreement_rate = sum(r["judge"]["agreement_rate"] for r in results) / total
    avg_faithfulness = sum(r["ragas"]["faithfulness"] for r in results) / total
    avg_relevancy = sum(r["ragas"]["relevancy"] for r in results) / total
    avg_latency = sum(r["latency"] for r in results) / total
    total_tokens = sum(r["tokens_used"] for r in results)
    total_cost = sum(r["cost_usd"] for r in results)

    summary = {
        "metadata": {
            "version": agent_version, 
            "total": total, 
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        },
        "metrics": {
            "avg_score": avg_score,
            "hit_rate": hit_rate,
            "agreement_rate": agreement_rate,
            "avg_faithfulness": avg_faithfulness,
            "avg_relevancy": avg_relevancy,
            "avg_latency": avg_latency,
            "total_tokens": total_tokens,
            "total_cost_usd": total_cost
        }
    }
    return results, summary

async def run_benchmark(version):
    _, summary = await run_benchmark_with_results(version)
    return summary

async def main():
    # 1. Chạy Benchmark cho Agent Base V1
    v1_results, v1_summary = await run_benchmark_with_results("Agent_V1_Base")
    
    # 2. Chạy Benchmark cho Agent Optimized V2
    v2_results, v2_summary = await run_benchmark_with_results("Agent_V2_Optimized")
    
    if not v1_results or not v2_results:
        print("❌ Không thể chạy Benchmark. Kiểm tra lại data/golden_set.jsonl.")
        return

    print("\n📊 --- KẾT QUẢ SO SÁNH (REGRESSION DELTA ANALYSIS) ---")
    delta = v2_summary["metrics"]["avg_score"] - v1_summary["metrics"]["avg_score"]
    
    print(f"==================================================")
    print(f"Chỉ số              | Agent V1 (Base) | Agent V2 (Optimized) | Chênh lệch (Delta)")
    print(f"--------------------------------------------------")
    print(f"Điểm Judge (1-5)   | {v1_summary['metrics']['avg_score']:.2f}            | {v2_summary['metrics']['avg_score']:.2f}                 | {delta:+.2f}")
    print(f"Retrieval Hit Rate  | {v1_summary['metrics']['hit_rate']*100:.1f}%           | {v2_summary['metrics']['hit_rate']*100:.1f}%            | {(v2_summary['metrics']['hit_rate'] - v1_summary['metrics']['hit_rate'])*100:+.1f}%")
    print(f"Độ đồng thuận Judge  | {v1_summary['metrics']['agreement_rate']*100:.1f}%           | {v2_summary['metrics']['agreement_rate']*100:.1f}%            | {(v2_summary['metrics']['agreement_rate'] - v1_summary['metrics']['agreement_rate'])*100:+.1f}%")
    print(f"Faithfulness (0-1)  | {v1_summary['metrics']['avg_faithfulness']:.2f}            | {v2_summary['metrics']['avg_faithfulness']:.2f}                 | {v2_summary['metrics']['avg_faithfulness'] - v1_summary['metrics']['avg_faithfulness']:+.2f}")
    print(f"Answer Relevancy    | {v1_summary['metrics']['avg_relevancy']:.2f}            | {v2_summary['metrics']['avg_relevancy']:.2f}                 | {v2_summary['metrics']['avg_relevancy'] - v1_summary['metrics']['avg_relevancy']:+.2f}")
    print(f"Độ trễ trung bình   | {v1_summary['metrics']['avg_latency']:.3f}s           | {v2_summary['metrics']['avg_latency']:.3f}s            | {v2_summary['metrics']['avg_latency'] - v1_summary['metrics']['avg_latency']:+.3f}s")
    print(f"Tổng Tokens tiêu thụ | {v1_summary['metrics']['total_tokens']}          | {v2_summary['metrics']['total_tokens']}           | {v2_summary['metrics']['total_tokens'] - v1_summary['metrics']['total_tokens']:+d}")
    print(f"Tổng Chi phí (USD)  | ${v1_summary['metrics']['total_cost_usd']:.5f}        | ${v2_summary['metrics']['total_cost_usd']:.5f}          | ${v2_summary['metrics']['total_cost_usd'] - v1_summary['metrics']['total_cost_usd']:+.5f}")
    print(f"==================================================")

    # Ghi nhận các file báo cáo
    os.makedirs("reports", exist_ok=True)
    with open("reports/summary.json", "w", encoding="utf-8") as f:
        json.dump(v2_summary, f, ensure_ascii=False, indent=2)
    with open("reports/benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump(v2_results, f, ensure_ascii=False, indent=2)
        
    with open("reports/summary_v1.json", "w", encoding="utf-8") as f:
        json.dump(v1_summary, f, ensure_ascii=False, indent=2)
    with open("reports/benchmark_results_v1.json", "w", encoding="utf-8") as f:
        json.dump(v1_results, f, ensure_ascii=False, indent=2)

    # Logic Release Gate
    # Chấp nhận release nếu điểm Judge tăng (delta > 0) VÀ hit rate không suy giảm nghiêm trọng
    hit_rate_delta = v2_summary["metrics"]["hit_rate"] - v1_summary["metrics"]["hit_rate"]
    
    if delta > 0 and hit_rate_delta >= -0.05:
        print("✅ QUYẾT ĐỊNH: CHẤP NHẬN BẢN CẬP NHẬT (APPROVE RELEASE)")
    else:
        print("❌ QUYẾT ĐỊNH: TỪ CHỐI BẢN CẬP NHẬT (BLOCK RELEASE / ROLLBACK)")

if __name__ == "__main__":
    asyncio.run(main())
