#!/usr/bin/env python3
"""
TechCorp FTE Prototype Test Suite
Tests the agent prototype with diverse scenarios
"""

import json
import sys
from typing import Dict, List, Any
from agent_prototype import TechCorpAgent

class PrototypeTester:
    def __init__(self):
        """Initialize the test suite"""
        self.agent = TechCorpAgent()
        self.test_results = []
    
    def load_test_cases(self, filepath: str) -> List[Dict]:
        """Load test cases from JSON file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                all_tickets = json.load(f)
            
            # Select 6 diverse test cases as specified
            test_cases = [
                # 1. Normal question (technical)
                next((t for t in all_tickets if t['id'] == 'T001'), all_tickets[0]),
                # 2. WhatsApp short message
                next((t for t in all_tickets if t['channel'] == 'whatsapp' and len(t['message']) < 50), all_tickets[1]),
                # 3. Refund request (escalation)
                next((t for t in all_tickets if 'refund' in t['message'].lower()), all_tickets[3]),
                # 4. Follow-up question (feature request)
                next((t for t in all_tickets if t['id'] == 'T007'), all_tickets[6]),
                # 5. API question
                next((t for t in all_tickets if t['category'] == 'api'), all_tickets[14]),
                # 6. Angry customer (escalation)
                next((t for t in all_tickets if 'angry' in t['notes'].lower() or 'furious' in t['message'].lower()), all_tickets[25])
            ]
            
            return test_cases
            
        except FileNotFoundError:
            print(f"❌ Test cases file {filepath} not found")
            return []
        except Exception as e:
            print(f"❌ Error loading test cases: {e}")
            return []
    
    def run_single_test(self, test_case: Dict, test_number: int) -> Dict[str, Any]:
        """Run a single test case"""
        try:
            # Extract customer info
            customer_id = test_case.get('customer_email') or test_case.get('customer_phone') or f"customer_{test_number}"
            message = test_case['message']
            channel = test_case['channel']
            
            # Run agent
            result = self.agent.run_agent(customer_id, message, channel)
            
            # Prepare test result
            test_result = {
                'test_number': test_number,
                'channel': channel,
                'customer_message': message,
                'response': result['response'],
                'escalated': result['escalated'],
                'ticket_id': result['ticket_id'],
                'escalation_reason': result.get('escalation_reason'),
                'expected_escalation': test_case.get('expected_escalation', False),
                'expected_action': test_case.get('expected_action', 'answer'),
                'category': test_case.get('category', 'unknown'),
                'error': None
            }
            
            # Validate escalation
            if test_case.get('expected_escalation') == True and not result['escalated']:
                test_result['error'] = "Expected escalation but didn't escalate"
            elif test_case.get('expected_escalation') == False and result['escalated']:
                test_result['error'] = "Escalated unexpectedly"
            
            return test_result
            
        except Exception as e:
            return {
                'test_number': test_number,
                'channel': test_case.get('channel', 'unknown'),
                'customer_message': test_case.get('message', ''),
                'response': '',
                'escalated': False,
                'ticket_id': None,
                'escalation_reason': None,
                'expected_escalation': test_case.get('expected_escalation', False),
                'expected_action': test_case.get('expected_action', 'answer'),
                'category': test_case.get('category', 'unknown'),
                'error': str(e)
            }
    
    def print_test_result(self, result: Dict[str, Any]):
        """Print individual test result"""
        status = "✅" if result['error'] is None else "❌"
        escalation_status = "🚨" if result['escalated'] else "💬"
        
        print(f"\n{status} Test {result['test_number']}: {result['channel'].upper()} {escalation_status}")
        print(f"   Customer: {result['customer_message'][:80]}{'...' if len(result['customer_message']) > 80 else ''}")
        print(f"   Response: {result['response'][:150]}{'...' if len(result['response']) > 150 else ''}")
        print(f"   Escalated: {'Yes' if result['escalated'] else 'No'}")
        
        if result['escalated']:
            print(f"   Reason: {result['escalation_reason']}")
        
        print(f"   Ticket: {result['ticket_id']}")
        print(f"   Category: {result['category']}")
        
        if result['error']:
            print(f"   ❌ Error: {result['error']}")
    
    def print_summary(self, results: List[Dict[str, Any]]):
        """Print comprehensive test summary"""
        total_tests = len(results)
        passed_tests = sum(1 for r in results if r['error'] is None)
        failed_tests = total_tests - passed_tests
        escalated_tests = sum(1 for r in results if r['escalated'])
        escalation_rate = (escalated_tests / total_tests) * 100 if total_tests > 0 else 0
        
        print("\n" + "=" * 60)
        print("📊 PROTOTYPE TEST SUMMARY")
        print("=" * 60)
        
        print(f"📈 Overall Results:")
        print(f"   Total tests: {total_tests}")
        print(f"   ✅ Passed: {passed_tests}")
        print(f"   ❌ Failed: {failed_tests}")
        print(f"   📊 Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        print(f"\n🚨 Escalation Analysis:")
        print(f"   Escalated: {escalated_tests}/{total_tests}")
        print(f"   Escalation Rate: {escalation_rate:.1f}%")
        
        # Channel breakdown
        channel_stats = {}
        for result in results:
            channel = result['channel']
            if channel not in channel_stats:
                channel_stats[channel] = {'total': 0, 'escalated': 0}
            channel_stats[channel]['total'] += 1
            if result['escalated']:
                channel_stats[channel]['escalated'] += 1
        
        print(f"\n📋 Channel Breakdown:")
        for channel, stats in channel_stats.items():
            rate = (stats['escalated'] / stats['total']) * 100 if stats['total'] > 0 else 0
            print(f"   {channel.capitalize()}: {stats['escalated']}/{stats['total']} escalated ({rate:.1f}%)")
        
        # Category breakdown
        category_stats = {}
        for result in results:
            category = result['category']
            if category not in category_stats:
                category_stats[category] = {'total': 0, 'escalated': 0}
            category_stats[category]['total'] += 1
            if result['escalated']:
                category_stats[category]['escalated'] += 1
        
        print(f"\n🏷️  Category Breakdown:")
        for category, stats in category_stats.items():
            rate = (stats['escalated'] / stats['total']) * 100 if stats['total'] > 0 else 0
            print(f"   {category.capitalize()}: {stats['escalated']}/{stats['total']} escalated ({rate:.1f}%)")
        
        # Errors
        if failed_tests > 0:
            print(f"\n❌ Errors Found:")
            for result in results:
                if result['error']:
                    print(f"   Test {result['test_number']}: {result['error']}")
        
        # Performance indicators
        print(f"\n⚡ Performance Indicators:")
        avg_response_length = sum(len(r['response']) for r in results) / total_tests
        print(f"   Average response length: {avg_response_length:.0f} characters")
        
        whatsapp_responses = [r for r in results if r['channel'] == 'whatsapp']
        if whatsapp_responses:
            whatsapp_compliance = sum(1 for r in whatsapp_responses if len(r['response']) <= 300) / len(whatsapp_responses) * 100
            print(f"   WhatsApp 300-char compliance: {whatsapp_compliance:.1f}%")
        
        print(f"\n🎯 Test Completion: {'SUCCESS' if failed_tests == 0 else 'NEEDS ATTENTION'}")
    
    def run_all_tests(self):
        """Run all test cases and generate report"""
        print("🧪 TechCorp FTE Agent Prototype Test Suite")
        print("=" * 50)
        
        # Load test cases
        test_cases = self.load_test_cases('context/sample-tickets.json')
        
        if not test_cases:
            print("❌ No test cases available. Exiting.")
            return
        
        print(f"📋 Loaded {len(test_cases)} test cases")
        print("🚀 Starting prototype testing...\n")
        
        # Run tests
        results = []
        for i, test_case in enumerate(test_cases, 1):
            print(f"Running test {i}/{len(test_cases)}...")
            result = self.run_single_test(test_case, i)
            results.append(result)
            self.print_test_result(result)
        
        # Store results
        self.test_results = results
        
        # Print summary
        self.print_summary(results)
        
        return results

def main():
    """Main test runner"""
    try:
        tester = PrototypeTester()
        results = tester.run_all_tests()
        
        # Return exit code based on results
        failed_tests = sum(1 for r in results if r['error'] is not None)
        if failed_tests > 0:
            print(f"\n⚠️  {failed_tests} test(s) failed. Review needed.")
            sys.exit(1)
        else:
            print(f"\n✅ All tests passed! Prototype working correctly.")
            sys.exit(0)
            
    except Exception as e:
        print(f"\n💥 Test suite failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
