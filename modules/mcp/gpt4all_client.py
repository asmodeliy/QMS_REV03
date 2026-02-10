
import json
import os
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

try:
    from gpt4all import GPT4All
    GPT4ALL_AVAILABLE = True
except ImportError:
    GPT4ALL_AVAILABLE = False
    print("Warning: gpt4all not installed. Install with: pip install gpt4all")

from modules.mcp.server import (
    list_projects,
    get_project_details,
    list_tasks,
    get_task_details,
    get_project_summary,
    list_users,
    list_issues,
    get_issue_details,
    list_shuttles,
    list_rpmt_projects,
    list_rpmt_tasks,
    get_pdk_dk_entries,
    list_customers,
    list_customer_issues,
    get_issue_conversations,
    list_spec_categories,
    list_spec_files,
    search_spec_content
)

try:
    from modules.mcp.rag_retriever import RAGRetriever
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    print("Warning: RAG retriever not available")


class QMSAssistant:
    """QMS Assistant with RAG-enhanced GPT4All integration"""
    
    def __init__(
        self, 
        model_name: str = "Meta-Llama-3-8B-Instruct.Q5_K_M",
        model_path: Optional[str] = r"C:\Users\이상원\Downloads\Models",
        enable_rag: bool = True,
        rag_db_path: str = "rag_knowledge_base.db"
    ):
        """Initialize QMS Assistant
        
        Args:
            model_name: Name of the GPT4All model
            model_path: Path to model directory
            enable_rag: If True, enable RAG context injection
            rag_db_path: Path to RAG knowledge base database
        """
        if not GPT4ALL_AVAILABLE:
            raise ImportError("gpt4all is not installed. Install with: pip install gpt4all")
        
        self.model_name = model_name
        
        if model_path is None:
            model_path = os.environ.get('GPT4ALL_MODEL_PATH')
        
        self.model_path = model_path
        self.model = None
        self.conversation_history = []
        
        # Initialize RAG
        self.enable_rag = enable_rag and RAG_AVAILABLE
        self.rag_retriever = None
        if self.enable_rag:
            try:
                from modules.mcp.rag_indexer import RAGIndexer
                indexer = RAGIndexer(db_path=rag_db_path)
                self.rag_retriever = RAGRetriever(indexer=indexer, db_path=rag_db_path)
            except Exception as e:
                print(f"Warning: RAG initialization failed: {e}")
                self.enable_rag = False
        
        self.tools = {
            "list_projects": {
                "function": list_projects,
                "description": "List all projects in the QMS system. Parameters: active_only (bool), limit (int)",
                "parameters": ["active_only", "limit"]
            },
            "get_project_details": {
                "function": get_project_details,
                "description": "Get detailed information about a specific project. Parameters: project_id (int)",
                "parameters": ["project_id"]
            },
            "list_tasks": {
                "function": list_tasks,
                "description": "List tasks in QMS. Parameters: project_id (int), status (str), limit (int)",
                "parameters": ["project_id", "status", "limit"]
            },
            "get_task_details": {
                "function": get_task_details,
                "description": "Get detailed task information. Parameters: task_id (int)",
                "parameters": ["task_id"]
            },
            "get_project_summary": {
                "function": get_project_summary,
                "description": "Get system-wide statistics. No parameters required.",
                "parameters": []
            },
            "list_users": {
                "function": list_users,
                "description": "List users in the system. Parameters: active_only (bool), limit (int)",
                "parameters": ["active_only", "limit"]
            },
            "list_issues": {
                "function": list_issues,
                "description": "List SVIT issues. Parameters: status (str), shuttle_id (str), limit (int)",
                "parameters": ["status", "shuttle_id", "limit"]
            },
            "get_issue_details": {
                "function": get_issue_details,
                "description": "Get detailed SVIT issue information. Parameters: tracking_no (str)",
                "parameters": ["tracking_no"]
            },
            "list_shuttles": {
                "function": list_shuttles,
                "description": "List SVIT shuttles. Parameters: limit (int)",
                "parameters": ["limit"]
            },
            # RPMT Tools
            "list_rpmt_projects": {
                "function": list_rpmt_projects,
                "description": "List RPMT projects. Parameters: active_only (bool), limit (int)",
                "parameters": ["active_only", "limit"]
            },
            "list_rpmt_tasks": {
                "function": list_rpmt_tasks,
                "description": "List RPMT tasks. Parameters: project_code (str), status (str), limit (int)",
                "parameters": ["project_code", "status", "limit"]
            },
            "get_pdk_dk_entries": {
                "function": get_pdk_dk_entries,
                "description": "List PDK/DK verification entries. Parameters: project_code (str), limit (int)",
                "parameters": ["project_code", "limit"]
            },
            # CITS Tools
            "list_customers": {
                "function": list_customers,
                "description": "List customers in CITS. Parameters: active_only (bool), limit (int)",
                "parameters": ["active_only", "limit"]
            },
            "list_customer_issues": {
                "function": list_customer_issues,
                "description": "List customer issues. Parameters: status (str), limit (int)",
                "parameters": ["status", "limit"]
            },
            "get_issue_conversations": {
                "function": get_issue_conversations,
                "description": "Get issue conversations. Parameters: ticket_no (str)",
                "parameters": ["ticket_no"]
            },
            # Spec-Center Tools
            "list_spec_categories": {
                "function": list_spec_categories,
                "description": "List specification categories. Parameters: parent_only (bool), limit (int)",
                "parameters": ["parent_only", "limit"]
            },
            "list_spec_files": {
                "function": list_spec_files,
                "description": "List specification files. Parameters: category_id (int), limit (int)",
                "parameters": ["category_id", "limit"]
            },
            "search_spec_content": {
                "function": search_spec_content,
                "description": "Search specification content by keyword. Parameters: keyword (str), limit (int)",
                "parameters": ["keyword", "limit"]
            }
        }
    
    def load_model(self):
        if self.model is None:
            print(f"Loading GPT4All model: {self.model_name}...")
            
            if self.model_path:
                print(f"Using model path: {self.model_path}")
                model_dir = Path(self.model_path)
                
                # 실제 GGUF 파일 찾기
                gguf_files = list(model_dir.glob("*.gguf"))
                
                if gguf_files:
                    # 첫 번째 GGUF 파일 사용
                    actual_model_file = gguf_files[0]
                    print(f"Found GGUF file: {actual_model_file.name}")
                    self.model = GPT4All(actual_model_file.name.replace('.gguf', ''), model_path=str(model_dir), allow_download=False, device='cpu')
                else:
                    print(f"Warning: No .gguf files found in {model_dir}")
                    print("Please download the model file first")
                    raise FileNotFoundError(f"No GGUF models found in {model_dir}")
            else:
                print("Using default GPT4All model cache directory")
                print("This may take a few minutes on first run as the model downloads...")
                self.model = GPT4All(self.model_name, device='cpu')
            
            print("Model loaded successfully!")
    
    def _create_system_prompt(self, use_rag_context: bool = True) -> str:
        """Create the system prompt with available tools and RAG context
        
        Args:
            use_rag_context: If True, include RAG-retrieved context
        
        Returns:
            System prompt string
        """
        tools_desc = "\n".join([
            f"- {name}: {info['description']}"
            for name, info in self.tools.items()
        ])
        
        base_prompt = f"""당신은 QMS(Quality Management System) 지원 AI 어시스턴트입니다. 한국어와 영어를 모두 유창하게 사용합니다.

사용 가능한 도구:

1. QMS 데이터베이스 조회 도구:
{tools_desc}

2. RAG 지식 기반 (프로젝트 문서 및 코드)

지침:
- 사용자 질문에 정확하고 친절하게 답변합니다
- 프로젝트/작업/사용자 정보가 필요하면 적절한 도구를 사용합니다
- 도구 호출은 JSON 형식: {{"tool": "tool_name", "parameters": {{"param1": "value1"}}}}
- 도구 결과를 받은 후 자연스러운 한국어/영어로 답변합니다
- 사용자 언어에 맞춰 응답합니다
- 전문적이고 정확한 답변을 제공합니다

You are a QMS (Quality Management System) support AI assistant fluent in both Korean and English.

Available Tools:

1. QMS Database Query Tools:
{tools_desc}

2. RAG Knowledge Base (Project documents and code)

Instructions:
- Answer user questions accurately and professionally
- Use appropriate tools when querying projects, tasks, or users
- Format tool calls as JSON: {{"tool": "tool_name", "parameters": {{"param1": "value1"}}}}
- Provide natural language responses in user's language after tool execution
- Respond in the user's language (Korean or English)
- Always provide accurate and helpful answers."""
        
        # Add RAG context if available
        if use_rag_context and self.enable_rag and self.rag_retriever:
            try:
                arch_context = self.rag_retriever.get_system_architecture_context()
                base_prompt = f"{base_prompt}\n\n{arch_context}"
            except Exception as e:
                print(f"Warning: Failed to add RAG context: {e}")
        
        return base_prompt
    
    def _parse_tool_call(self, response: str) -> Optional[Dict[str, Any]]:

        # Try to find JSON in the response
        try:
            # Look for JSON patterns
            start = response.find('{')
            end = response.rfind('}') + 1
            if start >= 0 and end > start:
                json_str = response[start:end]
                tool_call = json.loads(json_str)
                if 'tool' in tool_call:
                    return tool_call
        except json.JSONDecodeError:
            pass
        
        return None
    
    def _execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """Execute a tool with given parameters"""
        if tool_name not in self.tools:
            return {"error": f"Unknown tool: {tool_name}"}
        
        tool_info = self.tools[tool_name]
        try:
            # Filter parameters to only include valid ones
            valid_params = {
                k: v for k, v in parameters.items()
                if k in tool_info['parameters']
            }
            result = tool_info['function'](**valid_params)
            return result
        except Exception as e:
            return {"error": str(e)}
    
    def chat(self, user_message: str, max_iterations: int = 1, use_rag: bool = False, max_tokens: int = 64) -> str:
        """Chat with the assistant - with proper tool detection and execution
        
        Args:
            user_message: The message from the user
            max_iterations: Maximum number of tool iterations (unused)
            use_rag: Whether to use RAG context
            max_tokens: Maximum tokens to generate (default: 128 for faster response)
        """
        import time
        t0 = time.time()
        
        if self.model is None:
            self.load_model()
        
        t1 = time.time()
        self.conversation_history.append({"role": "user", "content": user_message})
        msg_lower = user_message.lower()
        
        print(f"[PERF] Chat init: {(t1-t0)*1000:.1f}ms")
        
        # ALWAYS prioritize actual database queries over LLM responses
        # Check in order of specificity: module-specific first, then general keywords
        
        # 1. SVIT (Silicon Verification Issue Tracking)
        if any(w in msg_lower for w in ['이슈', 'issue', 'svit', 'shuttle', '셔틀', 'verification', '검증', 'tracking_no', 'tracking no', 'hvit']):
            t_tool = time.time()
            print(f"[Chat] → SVIT query detected")
            if 'power' in msg_lower or any(w in msg_lower for w in ['shuttle', '셔틀']) and 'issue' not in msg_lower:
                shuttles = self._execute_tool('list_shuttles', {'limit': 20})
                response = self._format_shuttles_response(shuttles)
            elif any(w in msg_lower for w in ['상세', 'detail', 'tracking_no', 'tracking no']):
                issues = self._execute_tool('list_issues', {'limit': 1})
                if issues and len(issues) > 0 and 'tracking_no' in issues[0]:
                    issue_details = self._execute_tool('get_issue_details', {'tracking_no': issues[0]['tracking_no']})
                    response = self._format_issue_details_response(issue_details)
                else:
                    response = "이슈 상세정보를 찾을 수 없습니다."
            else:
                issues = self._execute_tool('list_issues', {'limit': 20})
                response = self._format_issues_response(issues)
            print(f"[PERF] SVIT tool exec: {(time.time()-t_tool)*1000:.1f}ms")
            self.conversation_history.append({"role": "assistant", "content": response})
            return response
        
        # 2. RPMT (Risk & Project Management)
        elif any(w in msg_lower for w in ['rpmt', 'pdk', 'dk', 'engineer', 'qa', '위험', '리스크', 'risk', 'verification', 'kickoff']):
            t_tool = time.time()
            print(f"[Chat] → RPMT query detected")
            if any(w in msg_lower for w in ['task', 'pdk', 'dk']):
                tasks = self._execute_tool('list_rpmt_tasks', {'limit': 20})
                response = self._format_rpmt_tasks_response(tasks)
            else:
                projects = self._execute_tool('list_rpmt_projects', {'limit': 20})
                response = self._format_rpmt_projects_response(projects)
            print(f"[PERF] RPMT tool exec: {(time.time()-t_tool)*1000:.1f}ms")
            self.conversation_history.append({"role": "assistant", "content": response})
            return response
        
        # 3. CITS (Customer Issue Tracking System)
        elif any(w in msg_lower for w in ['cits', 'customer', '고객', 'ticket', '티켓', 'claim', '클레임', 'support', '지원']):
            t_tool = time.time()
            print(f"[Chat] → CITS query detected")
            if any(w in msg_lower for w in ['customer', '고객']):
                customers = self._execute_tool('list_customers', {'limit': 20})
                response = self._format_customers_response(customers)
            elif any(w in msg_lower for w in ['conversation', 'reply', '답변', 'ticket no', 'ticket_no']):
                issues = self._execute_tool('list_customer_issues', {'limit': 1})
                if issues and len(issues) > 0 and 'ticket_no' in issues[0]:
                    convo = self._execute_tool('get_issue_conversations', {'ticket_no': issues[0]['ticket_no']})
                    response = self._format_conversations_response(convo)
                else:
                    response = "고객 이슈를 찾을 수 없습니다."
            else:
                issues = self._execute_tool('list_customer_issues', {'limit': 20})
                response = self._format_customer_issues_response(issues)
            print(f"[PERF] CITS tool exec: {(time.time()-t_tool)*1000:.1f}ms")
            self.conversation_history.append({"role": "assistant", "content": response})
            return response
        
        # 4. Spec-Center (Specification Management)
        elif any(w in msg_lower for w in ['spec', 'specification', '사양', '스펙', 'category', '분류', 'iso', '26262', 'aec', 'q100', 'standard', '표준']):
            t_tool = time.time()
            print(f"[Chat] → Spec-Center query detected")
            
            # Search for specific standards/keywords in documents
            if any(w in msg_lower for w in ['iso', '26262', 'aec', 'q100', 'standard', '표준']):
                # Extract search keyword from message
                search_keyword = self._extract_spec_keyword(user_message)
                
                print(f"[Chat] → Searching for spec file: {search_keyword}")
                # Try to find actual file first
                response = self._find_and_provide_spec_file(search_keyword)
                
                if not response:
                    # Fallback: search in RAG
                    results = self._execute_tool('search_spec_content', {'keyword': search_keyword, 'limit': 5})
                    response = self._format_spec_content_response(results, search_keyword)
            elif any(w in msg_lower for w in ['file', '파일']):
                files = self._execute_tool('list_spec_files', {'limit': 20})
                response = self._format_spec_files_response(files)
            else:
                categories = self._execute_tool('list_spec_categories', {'limit': 20})
                response = self._format_spec_categories_response(categories)
            print(f"[PERF] Spec-Center tool exec: {(time.time()-t_tool)*1000:.1f}ms")
            self.conversation_history.append({"role": "assistant", "content": response})
            return response
        
        # 5. Summary/Module count questions
        elif any(w in msg_lower for w in ['모듈', 'module', '수', 'count', '요약', 'summary', 
                                         '통계', 'statistic', 'overview', '전체', 'total']):
            t_tool = time.time()
            print(f"[Chat] → Summary query detected")
            summary = self._execute_tool('get_project_summary', {})
            response = self._format_summary_response(summary)
            print(f"[PERF] Summary tool exec: {(time.time()-t_tool)*1000:.1f}ms")
            self.conversation_history.append({"role": "assistant", "content": response})
            return response
        
        # 6. Project list questions
        elif any(w in msg_lower for w in ['프로젝트', 'project', '활성', 'active', '비활성']):
            t_tool = time.time()
            print(f"[Chat] → Project list query detected")
            projects = self._execute_tool('list_projects', {'active_only': True, 'limit': 20})
            response = self._format_projects_response(projects)
            print(f"[PERF] Project tool exec: {(time.time()-t_tool)*1000:.1f}ms")
            self.conversation_history.append({"role": "assistant", "content": response})
            return response
        
        # 7. Task/work questions  
        elif any(w in msg_lower for w in ['작업', 'task', 'work', '진행', 'progress']):
            t_tool = time.time()
            print(f"[Chat] → Task list query detected")
            tasks = self._execute_tool('list_tasks', {'project_id': None, 'status': None, 'limit': 20})
            response = self._format_tasks_response(tasks)
            print(f"[PERF] Task tool exec: {(time.time()-t_tool)*1000:.1f}ms")
            self.conversation_history.append({"role": "assistant", "content": response})
            return response
        
        # 8. User/people questions
        elif any(w in msg_lower for w in ['사용자', 'user', 'team', '팀', 'member', '멤버', 'people']):
            t_tool = time.time()
            print(f"[Chat] → User list query detected")
            users = self._execute_tool('list_users', {'active_only': True, 'limit': 20})
            response = self._format_users_response(users)
            print(f"[PERF] User tool exec: {(time.time()-t_tool)*1000:.1f}ms")
            self.conversation_history.append({"role": "assistant", "content": response})
            return response
        
        # 9. General LLM response for other questions
        else:
            t_llm = time.time()
            print(f"[Chat] → General conversation (generating with LLM)")
            response = self._generate_llm_response(user_message, max_tokens=max_tokens)
            print(f"[PERF] LLM generation: {(time.time()-t_llm)*1000:.1f}ms")
            self.conversation_history.append({"role": "assistant", "content": response})
            return response
    
    def _format_issues_response(self, data: Any) -> str:
        """Format SVIT issues into readable response"""
        if isinstance(data, list) and len(data) > 0:
            lines = [f"🔍 **SVIT 등록 이슈 목록** ({len(data)}개)\n"]
            for i, issue in enumerate(data[:15], 1):
                tracking_no = issue.get('tracking_no', 'N/A')
                shuttle_id = issue.get('shuttle_id', 'N/A')
                phenomenon = issue.get('issue_phenomenon', 'N/A')[:50]
                status = issue.get('status', 'NEW')
                status_emoji = {'NEW': '🆕', 'IN_PROGRESS': '⏳', 'PENDING_REVIEW': '👀', 'RESOLVED': '✅'}.get(status, '❓')
                lines.append(f"{i}. {status_emoji} **{tracking_no}** ({shuttle_id}) - {phenomenon}...")
            if len(data) > 15:
                lines.append(f"\n... 외 {len(data)-15}개 이슈")
            return "\n".join(lines)
        else:
            return "등록된 이슈가 없습니다."
    
    def _format_issue_details_response(self, data: Any) -> str:
        """Format detailed SVIT issue information"""
        if isinstance(data, dict) and 'error' not in data:
            return f"""📋 **이슈 상세정보**

**기본정보:**
• Tracking No: {data.get('tracking_no', 'N/A')}
• 셔틀: {data.get('shuttle_id', 'N/A')}
• Node: {data.get('node', 'N/A')}
• IP/IC: {data.get('ip_ic', 'N/A')}

**상태:**
• 현재상태: {data.get('status', 'N/A')}
• 담당자: {data.get('assignee', 'N/A')}
• 검토자: {data.get('reviewer', 'N/A')}

**이슈내용:**
• 현상: {data.get('issue_phenomenon', 'N/A')}
• 예상원인: {data.get('expected_root_cause', 'N/A')}
• 대책: {data.get('countermeasure', 'N/A')}

**타이밍:**
• 생성: {data.get('created_at', 'N/A')}
• 해결: {data.get('resolved_at', 'N/A')}"""
        else:
            return "이슈 상세정보를 조회할 수 없습니다."
    
    def _format_shuttles_response(self, data: Any) -> str:
        """Format shuttles into readable response"""
        if isinstance(data, list) and len(data) > 0:
            lines = [f"🚀 **셔틀 목록** ({len(data)}개)\n"]
            for i, shuttle in enumerate(data[:15], 1):
                shuttle_id = shuttle.get('shuttle_id', 'N/A')
                ip_ic = shuttle.get('ip_ic', 'N/A')
                node = shuttle.get('node', 'N/A')
                lines.append(f"{i}. **{shuttle_id}** - IP/IC: {ip_ic}, Node: {node}")
            if len(data) > 15:
                lines.append(f"\n... 외 {len(data)-15}개 셔틀")
            return "\n".join(lines)
        else:
            return "등록된 셔틀이 없습니다."
    
    def _format_summary_response(self, data: Any) -> str:
        """Format summary data into readable response"""
        if isinstance(data, dict) and 'error' not in data:
            return f"""📊 **QMS 시스템 현황**

**프로젝트 통계:**
• 전체: {data.get('total_projects', 0)}개
• 활성: {data.get('active_projects', 0)}개  
• 비활성: {data.get('inactive_projects', 0)}개

**작업 현황:**
• 전체: {data.get('total_tasks', 0)}개
• ✅ 완료: {data.get('task_status_distribution', {}).get('complete', 0)}개
• ⏳ 진행중: {data.get('task_status_distribution', {}).get('in_progress', 0)}개
• ⭕ 미시작: {data.get('task_status_distribution', {}).get('not_started', 0)}개
• ➖ NA: {data.get('task_status_distribution', {}).get('na', 0)}개

**📌 현재 운영 중인 QMS 모듈: 6개**
1️⃣ RPMT - 위험 및 프로젝트 관리
2️⃣ SVIT - 실리콘 검증 이슈 추적
3️⃣ CITS - 구성항목 추적
4️⃣ APQP - 고급 품질 계획
5️⃣ Spec-Center - 기술 사양 관리
6️⃣ Product-Info - 제품 정보 조회"""
        else:
            return "데이터를 조회할 수 없습니다."
    
    def _format_projects_response(self, data: Any) -> str:
        """Format project list into readable response"""
        if isinstance(data, list) and len(data) > 0:
            lines = [f"📋 **QMS 프로젝트 목록** ({len(data)}개)\n"]
            for i, proj in enumerate(data[:15], 1):
                code = proj.get('code', 'N/A')
                proc = proj.get('process', 'N/A')
                status = '✅활성' if proj.get('active') else '⛔비활성'
                lines.append(f"{i}. **{code}** ({proc}) - {status}")
            if len(data) > 15:
                lines.append(f"\n... 외 {len(data)-15}개 프로젝트")
            return "\n".join(lines)
        else:
            return "등록된 프로젝트가 없습니다."
    
    def _format_tasks_response(self, data: Any) -> str:
        """Format task list into readable response"""
        if isinstance(data, list) and len(data) > 0:
            lines = [f"✅ **작업 목록** ({len(data)}개)\n"]
            for i, task in enumerate(data[:15], 1):
                name = task.get('name', 'N/A')
                status = task.get('status', 'N/A')
                lines.append(f"{i}. {name} - {status}")
            if len(data) > 15:
                lines.append(f"\n... 외 {len(data)-15}개 작업")
            return "\n".join(lines)
        else:
            return "진행 중인 작업이 없습니다."
    
    def _format_users_response(self, data: Any) -> str:
        """Format user list into readable response"""
        if isinstance(data, list) and len(data) > 0:
            lines = [f"👥 **QMS 사용자** ({len(data)}명)\n"]
            for i, user in enumerate(data[:15], 1):
                name = user.get('english_name') or user.get('name', 'N/A')
                dept = user.get('department', '-')
                lines.append(f"{i}. {name} ({dept})")
            if len(data) > 15:
                lines.append(f"\n... 외 {len(data)-15}명")
            return "\n".join(lines)
        else:
            return "등록된 사용자가 없습니다."
    
    # ========== RPMT Formatters ==========
    def _format_rpmt_projects_response(self, data: Any) -> str:
        """Format RPMT projects into readable response"""
        if isinstance(data, list) and len(data) > 0:
            lines = [f"📊 **RPMT 프로젝트** ({len(data)}개)\n"]
            for i, proj in enumerate(data[:15], 1):
                code = proj.get('code', 'N/A')
                process = proj.get('process', '-')
                status = '✅활성' if proj.get('active') else '⛔비활성'
                lines.append(f"{i}. **{code}** ({process}) - {status}")
            if len(data) > 15:
                lines.append(f"\n... 외 {len(data)-15}개 프로젝트")
            return "\n".join(lines)
        else:
            return "등록된 RPMT 프로젝트가 없습니다."
    
    def _format_rpmt_tasks_response(self, data: Any) -> str:
        """Format RPMT tasks into readable response"""
        if isinstance(data, list) and len(data) > 0:
            lines = [f"✅ **RPMT 작업** ({len(data)}개)\n"]
            for i, task in enumerate(data[:15], 1):
                code = task.get('project_code', 'N/A')
                cat1 = task.get('cat1', 'N/A')
                status = task.get('status', 'N/A')
                status_emoji = {'Complete': '✅', 'In-progress': '⏳', 'Not Started': '🔵', 'N/A': '⚪'}.get(status, '❓')
                lines.append(f"{i}. {status_emoji} [{code}] {cat1}")
            if len(data) > 15:
                lines.append(f"\n... 외 {len(data)-15}개 작업")
            return "\n".join(lines)
        else:
            return "등록된 RPMT 작업이 없습니다."
    
    # ========== CITS Formatters ==========
    def _format_customers_response(self, data: Any) -> str:
        """Format customers into readable response"""
        if isinstance(data, list) and len(data) > 0:
            lines = [f"🏢 **고객사 목록** ({len(data)}개)\n"]
            for i, cust in enumerate(data[:15], 1):
                name = cust.get('name', 'N/A')
                company = cust.get('company', '-')
                status = '✅활성' if cust.get('is_active') else '⛔비활성'
                lines.append(f"{i}. **{name}** ({company}) - {status}")
            if len(data) > 15:
                lines.append(f"\n... 외 {len(data)-15}개 고객")
            return "\n".join(lines)
        else:
            return "등록된 고객사가 없습니다."
    
    def _format_customer_issues_response(self, data: Any) -> str:
        """Format customer issues into readable response"""
        if isinstance(data, list) and len(data) > 0:
            lines = [f"🎫 **고객 이슈** ({len(data)}개)\n"]
            for i, issue in enumerate(data[:15], 1):
                ticket = issue.get('ticket_no', 'N/A')
                title = issue.get('title', 'N/A')[:40]
                status = issue.get('status', 'OPEN')
                status_emoji = {'OPEN': '🔴', 'PENDING': '🟡', 'CLOSE': '🟢'}.get(status, '⚪')
                lines.append(f"{i}. {status_emoji} **{ticket}** - {title}...")
            if len(data) > 15:
                lines.append(f"\n... 외 {len(data)-15}개 이슈")
            return "\n".join(lines)
        else:
            return "등록된 고객 이슈가 없습니다."
    
    def _format_conversations_response(self, data: Any) -> str:
        """Format issue conversations into readable response"""
        if isinstance(data, dict) and 'error' not in data:
            lines = [f"💬 **이슈 대화 기록** ({data.get('ticket_no', 'N/A')})\n"]
            lines.append(f"제목: {data.get('title', 'N/A')}")
            lines.append(f"상태: {data.get('status', 'N/A')}")
            lines.append(f"담당: {data.get('assignee', 'N/A')}")
            lines.append(f"\n({data.get('conversation_count', 0)}건의 대화)\n")
            
            for i, conv in enumerate(data.get('conversations', [])[:5], 1):
                conv_type = conv.get('type', 'N/A')
                content = conv.get('content', 'N/A')
                created_by = conv.get('created_by', '-')
                lines.append(f"{i}. [{conv_type}] {created_by}: {content}...")
            
            return "\n".join(lines)
        else:
            return "이슈 대화를 조회할 수 없습니다."
    
    # ========== Spec-Center Formatters ==========
    def _format_spec_categories_response(self, data: Any) -> str:
        """Format spec categories into readable response"""
        if isinstance(data, list) and len(data) > 0:
            lines = [f"📚 **사양 카테고리** ({len(data)}개)\n"]
            for i, cat in enumerate(data[:15], 1):
                name = cat.get('name', 'N/A')
                desc = cat.get('description', '-')
                lines.append(f"{i}. **{name}** - {desc[:40]}")
            if len(data) > 15:
                lines.append(f"\n... 외 {len(data)-15}개 카테고리")
            return "\n".join(lines)
        else:
            return "등록된 사양 카테고리가 없습니다."
    
    def _format_spec_files_response(self, data: Any) -> str:
        """Format spec files into readable response"""
        if isinstance(data, list) and len(data) > 0:
            lines = [f"📄 **사양 파일** ({len(data)}개)\n"]
            for i, file in enumerate(data[:15], 1):
                name = file.get('original_name', 'N/A')
                size_kb = file.get('file_size', 0) // 1024
                lines.append(f"{i}. **{name}** ({size_kb}KB)")
            if len(data) > 15:
                lines.append(f"\n... 외 {len(data)-15}개 파일")
            return "\n".join(lines)
        else:
            return "등록된 사양 파일이 없습니다."
    
    def _extract_spec_keyword(self, message: str) -> str:
        """Extract spec keyword from user message"""
        msg_lower = message.lower()
        
        # High priority keywords
        if 'iso' in msg_lower or '26262' in msg_lower:
            return 'ISO26262'
        if 'aec' in msg_lower or 'q100' in msg_lower:
            return 'AEC-Q100'
        if 'jesd' in msg_lower:
            return 'JESD'
        if 'htol' in msg_lower or 'high temp' in msg_lower:
            return 'HTOL'
        if 'hast' in msg_lower:
            return 'HAST'
        if 'esd' in msg_lower:
            return 'ESD'
        if 'rs-cop' in msg_lower or 'cop' in msg_lower:
            return 'RS-COP'
        if 'rs-qm' in msg_lower or 'quality' in msg_lower:
            return 'RS-QM'
        if 'rs-em' in msg_lower or 'environment' in msg_lower:
            return 'RS-EM'
        
        # Default
        return 'standard'
    
    def _find_and_provide_spec_file(self, keyword: str) -> Optional[str]:
        """Find spec file and provide download/view links"""
        try:
            from modules.spec_center.parser import SpecCenterParser
            
            parser = SpecCenterParser(spec_center_path="uploads/spec_center")
            
            # Load documents if needed
            if not parser.documents:
                if not parser.load_index(".spec_center_index.json"):
                    parser.parse_all_documents()
            
            # Find matching files
            files = parser.find_spec_files(keyword, limit=5)
            
            if not files:
                return None
            
            # Build response with file links
            lines = [f"📄 **{keyword} 관련 사양서 목록**\n"]
            
            for i, file_info in enumerate(files, 1):
                file_name = file_info.get('file_name', 'N/A')
                web_path = file_info.get('web_path', f"uploads/spec_center/{file_name}")
                keywords = file_info.get('keywords', [])
                
                # Create clickable link
                lines.append(f"{i}. [{file_name}]({web_path})")
                
                if keywords:
                    lines.append(f"   🏷️  {', '.join(keywords[:3])}")
            
            if len(files) > 5:
                lines.append(f"\n... 외 {len(files)-5}개 문서")
            
            return "\n".join(lines)
        
        except Exception as e:
            print(f"Error finding spec file: {e}")
            return None
    
    def _format_spec_content_response(self, data: Any, keyword: str) -> str:
        """Format spec content search results into readable response"""
        if isinstance(data, list) and len(data) > 0:
            # Check for errors
            if data[0].get('error'):
                return f"사양 검색 중 오류: {data[0]['error']}"
            
            lines = [f"📖 **{keyword} 관련 사양 문서**\n"]
            
            for i, result in enumerate(data[:5], 1):
                title = result.get('file_name', 'N/A').replace('_', ' ')
                keywords = result.get('keywords', [])
                preview = result.get('preview', '')[:150]
                
                lines.append(f"\n**{i}. {title}**")
                if keywords:
                    lines.append(f"   🏷️  {', '.join(keywords)}")
                if preview:
                    lines.append(f"   📝 {preview}...")
                
                # Add actual content if available
                content = result.get('content', '')
                if content and len(content) > 100:
                    lines.append(f"\n   **주요 내용:**")
                    # Split content into manageable chunks
                    content_lines = content.split('\n')
                    for content_line in content_lines[:5]:
                        if content_line.strip():
                            lines.append(f"   {content_line.strip()[:100]}")
            
            if len(data) > 5:
                lines.append(f"\n... 외 {len(data)-5}개 문서")
            
            return "\n".join(lines)
        else:
            keyword_display = keyword.replace('_', ' ') if keyword else "검색"
            return f"**{keyword_display}** 관련 문서를 찾을 수 없습니다."
    
    def _generate_llm_response(self, user_message: str, max_tokens: int = 64) -> str:
        """Generate response using LLM for general questions"""
        import time
        t0 = time.time()
        
        prompt = self._create_system_prompt(use_rag_context=False) + "\n\n"
        t1 = time.time()
        
        # Add RAG context if available
        if self.enable_rag and self.rag_retriever:
            try:
                t_rag = time.time()
                rag_ctx = self.rag_retriever.build_context(user_message, max_context_length=1000)
                print(f"[PERF] RAG context build: {(time.time()-t_rag)*1000:.1f}ms")
                if rag_ctx:
                    prompt += f"【관련 문서】\n{rag_ctx}\n\n"
            except Exception as e:
                print(f"[PERF] RAG error: {e}")
        
        t2 = time.time()
        
        # Add conversation context
        for msg in self.conversation_history[-3:]:
            prompt += f"{msg['role']}: {msg['content']}\n"
        prompt += "assistant: "
        
        t3 = time.time()
        print(f"[PERF] LLM prompt ({max_tokens} tokens): {(t3-t0)*1000:.1f}ms total (setup: {(t1-t0)*1000:.1f}ms, RAG: {(t2-t1)*1000:.1f}ms, context: {(t3-t2)*1000:.1f}ms)")
        
        t_gen = time.time()
        print(f"[PERF] Starting model.generate() with max_tokens={max_tokens}, temp=0.3")
        try:
            response = self.model.generate(prompt, max_tokens=max_tokens, temp=0.3)
            t_gen_end = time.time()
            gen_time = t_gen_end - t_gen
            print(f"[PERF] Model generation completed: {gen_time:.2f}s ({len(response)} chars)")
        except Exception as e:
            print(f"[PERF] Model generation ERROR: {e}")
            raise
        
        return response
    
    def reset_conversation(self):
        """Clear conversation history"""
        self.conversation_history = []
    
    def ask_about_projects(self, query: str = "Show me all active projects") -> str:
        """Quick method to ask about projects"""
        return self.chat(query)
    
    def ask_about_tasks(self, query: str = "What tasks are in progress?") -> str:
        """Quick method to ask about tasks"""
        return self.chat(query)
    
    def ask_for_summary(self, query: str = "Give me a summary of the QMS system") -> str:
        """Quick method to ask for system summary"""
        return self.chat(query)


def simple_chat_loop():
    """
    Simple command-line chat interface
    """
    print("=" * 60)
    print("QMS Assistant - Local GPT4All Integration")
    print("=" * 60)
    print()
    print("Initializing assistant...")
    
    try:
        assistant = QMSAssistant()
        assistant.load_model()
        
        print("\nAssistant ready! Type 'quit' to exit, 'reset' to clear history.")
        print("\nExample questions:")
        print("  - Show me all active projects")
        print("  - What's the status of project ID 6?")
        print("  - List all in-progress tasks")
        print("  - Give me a system summary")
        print()
        
        while True:
            user_input = input("\nYou: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break
            
            if user_input.lower() == 'reset':
                assistant.reset_conversation()
                print("Conversation history cleared.")
                continue
            
            if not user_input:
                continue
            
            print("\nAssistant: ", end="", flush=True)
            response = assistant.chat(user_input)
            print(response)
    
    except ImportError as e:
        print(f"\nError: {e}")
        print("\nTo use GPT4All, install it with:")
        print("  pip install gpt4all")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    simple_chat_loop()
