"""
Test script to evaluate pros and cons of Ollama service
Tests various aspects: performance, reliability, features, etc.
"""


import time
import json
import statistics
import concurrent.futures
from typing import List, Dict, Any
import requests
import traceback
from datetime import datetime


class OllamaClient:   
   def __init__(self, base_url: str = "http://localhost:11434"):
       self.base_url = base_url
      
   def generate(self, model: str, prompt: str, context: List[int] = None, stream: bool = False) -> Dict[str, Any]:
       url = f"{self.base_url}/api/generate"
       payload = {
           "model": model,
           "prompt": prompt,
           "stream": stream,
           "context": context or []
       }
      
       try:
           response = requests.post(url, json=payload, timeout=60)
           response.raise_for_status()
           return response.json()
       except requests.exceptions.RequestException as e:
           raise Exception(f"Ollama API error: {str(e)}")
  
   def chat(self, model: str, messages: List[Dict[str, str]], stream: bool = False) -> Dict[str, Any]:
       url = f"{self.base_url}/api/chat"
       payload = {
           "model": model,
           "messages": messages,
           "stream": stream
       }
      
       try:
           response = requests.post(url, json=payload, timeout=60)
           response.raise_for_status()
           return response.json()
       except requests.exceptions.RequestException as e:
           raise Exception(f"Ollama Chat API error: {str(e)}")


class OllamaServiceTester:
   def __init__(self, model: str = "llama3.2:3b"):
       self.client = OllamaClient()
       self.model = model
       self.results = {
           "pros": [],
           "cons": [],
           "metrics": {}
       }
      
   def test_response_time(self, num_tests: int = 5):
       """Test average response time"""
       print(f"\n🔍 Testing Response Time ({num_tests} iterations)...")
      
       prompts = [
           "What is 2+2?",
           "Explain quantum computing in one sentence.",
           "Write a haiku about programming.",
           "List 3 benefits of exercise.",
           "What is the capital of France?"
       ]
      
       response_times = []
      
       for i in range(min(num_tests, len(prompts))):
           prompt = prompts[i % len(prompts)]
           start_time = time.time()
          
           try:
               response = self.client.generate(self.model, prompt)
               elapsed = time.time() - start_time
               response_times.append(elapsed)
               print(f"  Test {i+1}: {elapsed:.2f}s")
           except Exception as e:
               print(f"  Test {i+1}: Failed - {str(e)}")
               self.results["cons"].append(f"Failed response on test {i+1}: {str(e)}")
      
       if response_times:
           avg_time = statistics.mean(response_times)
           self.results["metrics"]["avg_response_time"] = avg_time
          
           if avg_time < 2:
               self.results["pros"].append(f"Fast response time: avg {avg_time:.2f}s")
           elif avg_time > 5:
               self.results["cons"].append(f"Slow response time: avg {avg_time:.2f}s")
          
           print(f"  ✅ Average response time: {avg_time:.2f}s")
           print(f"  Min: {min(response_times):.2f}s, Max: {max(response_times):.2f}s")
      
   def test_concurrent_requests(self, num_concurrent: int = 3):
       """Test handling of concurrent requests"""
       print(f"\n🔍 Testing Concurrent Requests ({num_concurrent} simultaneous)...")
      
       def make_request(prompt):
           start = time.time()
           try:
               response = self.client.generate(self.model, prompt)
               return time.time() - start, True, None
           except Exception as e:
               return time.time() - start, False, str(e)
      
       prompts = [f"Count from 1 to {i+3}" for i in range(num_concurrent)]
      
       with concurrent.futures.ThreadPoolExecutor(max_workers=num_concurrent) as executor:
           futures = [executor.submit(make_request, prompt) for prompt in prompts]
           results = [f.result() for f in concurrent.futures.as_completed(futures)]
      
       successful = sum(1 for _, success, _ in results if success)
       failed = num_concurrent - successful
      
       if successful == num_concurrent:
           self.results["pros"].append(f"Handles {num_concurrent} concurrent requests well")
           print(f"  ✅ All {num_concurrent} concurrent requests succeeded")
       else:
           self.results["cons"].append(f"Failed {failed}/{num_concurrent} concurrent requests")
           print(f"  ⚠️ {failed}/{num_concurrent} concurrent requests failed")
          
       self.results["metrics"]["concurrent_success_rate"] = successful / num_concurrent
      
   def test_context_retention(self):
       """Test if context is properly retained between calls"""
       print("\n🔍 Testing Context Retention...")
      
       try:
           # First message
           messages = [
               {"role": "user", "content": "My name is Alice. Remember this."}
           ]
           response1 = self.client.chat(self.model, messages)
          
           # Add assistant response to conversation
           messages.append({"role": "assistant", "content": response1.get("message", {}).get("content", "")})
          
           # Second message testing context
           messages.append({"role": "user", "content": "What is my name?"})
           response2 = self.client.chat(self.model, messages)
          
           response_text = response2.get("message", {}).get("content", "").lower()
          
           if "alice" in response_text:
               self.results["pros"].append("Good context retention in conversations")
               print("  ✅ Context retained successfully")
           else:
               self.results["cons"].append("Poor context retention")
               print("  ⚠️ Context not retained properly")
              
       except Exception as e:
           self.results["cons"].append(f"Context test failed: {str(e)}")
           print(f"  ❌ Context test failed: {str(e)}")
  
   def test_error_handling(self):
       """Test error handling with invalid inputs"""
       print("\n🔍 Testing Error Handling...")
      
       test_cases = [
           ("Invalid model", "non_existent_model", "Test prompt"),
           ("Empty prompt", self.model, ""),
           ("Very long prompt", self.model, "x" * 10000)
       ]
      
       handled_well = 0
      
       for test_name, model, prompt in test_cases:
           try:
               response = self.client.generate(model, prompt)
               print(f"  {test_name}: Unexpectedly succeeded")
           except Exception as e:
               handled_well += 1
               print(f"  {test_name}: Properly caught error")
      
       if handled_well == len(test_cases):
           self.results["pros"].append("Good error handling for invalid inputs")
       else:
           self.results["cons"].append("Inconsistent error handling")
          
       self.results["metrics"]["error_handling_score"] = handled_well / len(test_cases)
  
   def test_streaming_capability(self):
       """Test streaming response capability"""
       print("\n🔍 Testing Streaming Capability...")
      
       try:
           url = f"{self.client.base_url}/api/generate"
           payload = {
               "model": self.model,
               "prompt": "Count from 1 to 5 slowly",
               "stream": True
           }
          
           response = requests.post(url, json=payload, stream=True, timeout=10)
           chunks_received = 0
          
           for line in response.iter_lines():
               if line:
                   chunks_received += 1
                   if chunks_received > 5:  # Just check we're getting chunks
                       break
          
           if chunks_received > 1:
               self.results["pros"].append("Supports streaming responses")
               print(f"  ✅ Streaming works ({chunks_received} chunks received)")
           else:
               self.results["cons"].append("Streaming not working properly")
               print("  ⚠️ Streaming issues detected")
              
       except Exception as e:
           self.results["cons"].append(f"Streaming test failed: {str(e)}")
           print(f"  ❌ Streaming test failed: {str(e)}")
  
   def test_model_availability(self):
       """Check if the model is available"""
       print("\n🔍 Testing Model Availability...")
      
       try:
           response = requests.get(f"{self.client.base_url}/api/tags")
           if response.status_code == 200:
               models = response.json().get("models", [])
               model_names = [m.get("name", "") for m in models]
              
               if any(self.model in name for name in model_names):
                   self.results["pros"].append(f"Model {self.model} is available")
                   print(f"  ✅ Model {self.model} is available")
               else:
                   self.results["cons"].append(f"Model {self.model} not found")
                   print(f"  ⚠️ Model {self.model} not in available models")
                  
               print(f"  Available models: {', '.join(model_names[:3])}...")
           else:
               self.results["cons"].append("Could not fetch available models")
              
       except Exception as e:
           self.results["cons"].append(f"Model check failed: {str(e)}")
           print(f"  ❌ Model availability check failed: {str(e)}")
  
   def test_response_quality(self):
       """Test quality of responses"""
       print("\n🔍 Testing Response Quality...")
      
       test_prompts = [
           ("Math", "What is 15 + 27?", "42"),
           ("Factual", "What is the capital of Japan?", "tokyo"),
           ("Logic", "If all roses are flowers and some flowers are red, can some roses be red?", "yes")
       ]
      
       correct = 0
      
       for category, prompt, expected in test_prompts:
           try:
               response = self.client.generate(self.model, prompt)
               answer = response.get("response", "").lower()
              
               if expected in answer:
                   correct += 1
                   print(f"  {category}: ✅ Correct")
               else:
                   print(f"  {category}: ❌ Incorrect")
                  
           except Exception as e:
               print(f"  {category}: Failed - {str(e)}")
      
       accuracy = correct / len(test_prompts)
       self.results["metrics"]["response_accuracy"] = accuracy
      
       if accuracy >= 0.8:
           self.results["pros"].append(f"Good response accuracy: {accuracy:.0%}")
       elif accuracy < 0.5:
           self.results["cons"].append(f"Poor response accuracy: {accuracy:.0%}")
  
   def run_all_tests(self):
       """Run all tests and generate report"""
       print("="*60)
       print(f"🚀 OLLAMA SERVICE TEST SUITE")
       print(f"Model: {self.model}")
       print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
       print("="*60)
      
       # Run all tests
       self.test_model_availability()
       self.test_response_time()
       self.test_concurrent_requests()
       self.test_context_retention()
       self.test_error_handling()
       self.test_streaming_capability()
       self.test_response_quality()
      
       # Generate report
       self.generate_report()
  
   def generate_report(self):
       """Generate final report with pros and cons"""
       print("\n" + "="*60)
       print("📊 FINAL REPORT")
       print("="*60)
      
       print("\n✅ PROS:")
       if self.results["pros"]:
           for i, pro in enumerate(self.results["pros"], 1):
               print(f"  {i}. {pro}")
       else:
           print("  No significant advantages found")
      
       print("\n❌ CONS:")
       if self.results["cons"]:
           for i, con in enumerate(self.results["cons"], 1):
               print(f"  {i}. {con}")
       else:
           print("  No significant disadvantages found")
      
       print("\n📈 METRICS:")
       for metric, value in self.results["metrics"].items():
           if isinstance(value, float):
               if "time" in metric:
                   print(f"  • {metric}: {value:.2f}s")
               elif "rate" in metric or "score" in metric or "accuracy" in metric:
                   print(f"  • {metric}: {value:.0%}")
               else:
                   print(f"  • {metric}: {value:.2f}")
           else:
               print(f"  • {metric}: {value}")
      
       print("\n" + "="*60)
      
       # Overall assessment
       pros_count = len(self.results["pros"])
       cons_count = len(self.results["cons"])
      
       if pros_count > cons_count * 1.5:
           print("🎯 OVERALL: RECOMMENDED - More advantages than disadvantages")
       elif cons_count > pros_count * 1.5:
           print("⚠️ OVERALL: USE WITH CAUTION - More disadvantages than advantages")
       else:
           print("⚖️ OVERALL: NEUTRAL - Balanced pros and cons")
      
       print("="*60)


if __name__ == "__main__":
   # You can change the model here
   tester = OllamaServiceTester(model="qwen3:14b")
  
   try:
       tester.run_all_tests()
   except KeyboardInterrupt:
       print("\n\n⚠️ Test interrupted by user")
   except Exception as e:
       print(f"\n\n❌ Test suite failed: {str(e)}")
       traceback.print_exc()

