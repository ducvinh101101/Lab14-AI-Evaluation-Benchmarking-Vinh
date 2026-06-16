import asyncio
import time
from typing import List, Dict

class BenchmarkRunner:
    def __init__(self, agent, evaluator, judge):
        self.agent = agent
        self.evaluator = evaluator
        self.judge = judge

    async def run_single_test(self, test_case: Dict) -> Dict:
        start_time = time.perf_counter()
        
        # 1. Gọi Agent
        response = await self.agent.query(test_case["question"])
        latency = time.perf_counter() - start_time
        
        # 2. Chạy RAGAS metrics (Faithfulness, Relevancy, Hit Rate, MRR)
        ragas_scores = await self.evaluator.score(test_case, response)
        
        # 3. Chạy Multi-Judge
        judge_result = await self.judge.evaluate_multi_judge(
            test_case["question"], 
            response["answer"], 
            test_case["expected_answer"]
        )
        
        # 4. Tính toán số lượng token & chi phí ước tính (Cost & Token tracking)
        # Giả lập token cho Agent
        agent_tokens = response.get("metadata", {}).get("tokens_used", 150)
        
        # Giả lập token cho LLM Judges:
        # Mỗi lượt gọi Judge gpt-4o/gpt-4o-mini tiêu tốn trung bình 400 input tokens + 120 output tokens
        # Nếu có xung đột (agreement_rate < 1.0), mô hình trọng tài Arbitrator sẽ được gọi (thêm ~500 input + 150 output tokens)
        judge_tokens = 2 * (400 + 120)
        if judge_result.get("agreement_rate", 1.0) < 1.0:
            judge_tokens += (500 + 150)
            
        # Token cho RAGAS Faithfulness/Relevancy (nếu chạy qua API): khoảng 300 input + 50 output
        eval_tokens = 350
        
        total_tokens = agent_tokens + judge_tokens + eval_tokens
        
        # Đơn giá (USD trên 1M tokens) cho gpt-4o: $5.00 input / $15.00 output
        # Đơn giá cho gpt-4o-mini: $0.15 input / $0.60 output
        # Ở đây ta ước tính chi phí hỗn hợp trung bình khoảng $0.000003 mỗi token (tức $3 / 1M tokens)
        cost_usd = total_tokens * 0.000003
        
        return {
            "test_case": test_case["question"],
            "agent_response": response["answer"],
            "latency": latency,
            "ragas": ragas_scores,
            "judge": judge_result,
            "tokens_used": total_tokens,
            "cost_usd": cost_usd,
            "status": "fail" if judge_result["final_score"] < 3 else "pass"
        }

    async def run_all(self, dataset: List[Dict], batch_size: int = 5) -> List[Dict]:
        """
        Chạy song song bằng asyncio.gather với giới hạn batch_size để không bị Rate Limit.
        """
        results = []
        for i in range(0, len(dataset), batch_size):
            batch = dataset[i:i + batch_size]
            tasks = [self.run_single_test(case) for case in batch]
            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)
        return results
