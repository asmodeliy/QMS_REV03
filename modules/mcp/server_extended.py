#!/usr/bin/env python3
"""
Extended MCP Server for QMS with CITS, RPMT, and SVIT database support.
"""

import os
import sqlite3
from typing import Any, Dict, List, Optional
from datetime import datetime

# Database paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
RPMT_DB = os.path.join(BASE_DIR, "database", "rpmt.db")
CITS_DB = os.path.join(BASE_DIR, "database", "cits.db")
SVIT_DB = os.path.join(BASE_DIR, "database", "svit.db")


def get_cits_customers() -> Dict[str, Any]:

    try:
        # Check if CITS database exists
        if not os.path.exists(CITS_DB):
            # Return sample data when database doesn't exist
            return {
                "note": "샘플 데이터 (실제 DB 연결 필요)",
                "customers": [
                    {
                        "id": 1,
                        "company": "Verisilicon",
                        "contact": "Dan",
                        "email": "example@verisilicon.com",
                        "phone": "010-1234-5678",
                        "address": "aaaaa",
                        "registered": "2024-01-15"
                    },
                    {
                        "id": 2,
                        "company": "Rockchip",
                        "contact": "bbb",
                        "email": "bbb@rockchip.com",
                        "phone": "010-2345-6789",
                        "address": "bbbbbb",
                        "registered": "2024-02-20"
                    },
                    {
                        "id": 3,
                        "company": "Glenfly",
                        "contact": "ccc",
                        "email": "eccc@glenfly.com",
                        "phone": "010-3456-7890",
                        "address": "ccccc",
                        "registered": "2024-03-10"
                    }
                ],
                "total": 3,
                "database": "cits.db (샘플 데이터)"
            }
        
        conn = sqlite3.connect(CITS_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Query customers from CITS database
        cursor.execute("""
            SELECT 
                id,
                company_name,
                contact_person,
                email,
                phone,
                address,
                created_at
            FROM customers
            ORDER BY company_name
        """)
        
        customers = []
        for row in cursor.fetchall():
            customers.append({
                "id": row["id"],
                "company": row["company_name"],
                "contact": row["contact_person"],
                "email": row["email"],
                "phone": row["phone"],
                "address": row["address"],
                "registered": row["created_at"]
            })
        
        conn.close()
        
        return {
            "customers": customers,
            "total": len(customers),
            "database": "cits.db",
            "query_time": datetime.now().isoformat()
        }
        
    except sqlite3.Error as e:
        return {
            "note": "샘플 데이터 (실제 DB 연결 필요)",
            "customers": [
                    {
                        "id": 1,
                        "company": "Verisilicon",
                        "contact": "Dan",
                        "email": "example@verisilicon.com",
                        "phone": "010-1234-5678",
                        "address": "aaaaa",
                        "registered": "2024-01-15"
                    },
                    {
                        "id": 2,
                        "company": "Rockchip",
                        "contact": "bbb",
                        "email": "bbb@rockchip.com",
                        "phone": "010-2345-6789",
                        "address": "bbbbbb",
                        "registered": "2024-02-20"
                    },
                    {
                        "id": 3,
                        "company": "Glenfly",
                        "contact": "ccc",
                        "email": "eccc@glenfly.com",
                        "phone": "010-3456-7890",
                        "address": "ccccc",
                        "registered": "2024-03-10"
                    }
            ],
            "total": 3,
            "database": "cits.db (샘플 데이터)"
        }


def get_rpmt_summary() -> Dict[str, Any]:

    try:
        if not os.path.exists(RPMT_DB):
            return {
                "note": "샘플 데이터 (실제 DB 연결 필요)",
                "summary": {
                    "projects": {
                        "total": 3,
                        "active": 2,
                        "completed": 1
                    },
                    "tasks": {
                        "total": 5,
                        "completed": 2,
                        "in_progress": 2,
                        "pending": 1
                    },
                    "users": {
                        "total": 4
                    }
                },
                "recent_projects": [
                    {
                        "id": 1,
                        "name": "QMS System Enhancement",
                        "status": "active",
                        "progress": 75
                    },
                    {
                        "id": 2,
                        "name": "AI Integration Project",
                        "status": "active",
                        "progress": 60
                    },
                    {
                        "id": 3,
                        "name": "Database Migration",
                        "status": "completed",
                        "progress": 100
                    }
                ],
                "recent_tasks": [
                    {
                        "id": 1,
                        "title": "Implement GPT4All integration",
                        "status": "completed",
                        "priority": "high"
                    },
                    {
                        "id": 2,
                        "title": "Create MCP server",
                        "status": "completed",
                        "priority": "high"
                    },
                    {
                        "id": 3,
                        "title": "Build offline packages",
                        "status": "in_progress",
                        "priority": "medium"
                    },
                    {
                        "id": 4,
                        "title": "Write documentation",
                        "status": "in_progress",
                        "priority": "medium"
                    },
                    {
                        "id": 5,
                        "title": "Setup HTTPS",
                        "status": "pending",
                        "priority": "low"
                    }
                ],
                "database": "rpmt.db (샘플 데이터)"
            }
        
        conn = sqlite3.connect(RPMT_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get project statistics
        cursor.execute("SELECT COUNT(*) as total FROM projects")
        total_projects = cursor.fetchone()["total"]
        
        cursor.execute("SELECT COUNT(*) as active FROM projects WHERE status='active'")
        active_projects = cursor.fetchone()["active"]
        
        # Get task statistics
        cursor.execute("SELECT COUNT(*) as total FROM tasks")
        total_tasks = cursor.fetchone()["total"]
        
        cursor.execute("SELECT COUNT(*) as completed FROM tasks WHERE status='completed'")
        completed_tasks = cursor.fetchone()["completed"]
        
        cursor.execute("SELECT COUNT(*) as in_progress FROM tasks WHERE status='in_progress'")
        in_progress_tasks = cursor.fetchone()["in_progress"]
        
        # Get user count
        cursor.execute("SELECT COUNT(*) as total FROM users")
        total_users = cursor.fetchone()["total"]
        
        # Get recent projects
        cursor.execute("""
            SELECT id, name, status, progress
            FROM projects
            ORDER BY updated_at DESC
            LIMIT 5
        """)
        recent_projects = []
        for row in cursor.fetchall():
            recent_projects.append({
                "id": row["id"],
                "name": row["name"],
                "status": row["status"],
                "progress": row["progress"]
            })
        
        # Get recent tasks
        cursor.execute("""
            SELECT id, title, status, priority
            FROM tasks
            ORDER BY updated_at DESC
            LIMIT 5
        """)
        recent_tasks = []
        for row in cursor.fetchall():
            recent_tasks.append({
                "id": row["id"],
                "title": row["title"],
                "status": row["status"],
                "priority": row["priority"]
            })
        
        conn.close()
        
        return {
            "summary": {
                "projects": {
                    "total": total_projects,
                    "active": active_projects,
                    "completed": total_projects - active_projects
                },
                "tasks": {
                    "total": total_tasks,
                    "completed": completed_tasks,
                    "in_progress": in_progress_tasks,
                    "pending": total_tasks - completed_tasks - in_progress_tasks
                },
                "users": {
                    "total": total_users
                }
            },
            "recent_projects": recent_projects,
            "recent_tasks": recent_tasks,
            "database": "rpmt.db",
            "query_time": datetime.now().isoformat()
        }
        
    except sqlite3.Error as e:
        # Return sample data
        return {
            "note": "샘플 데이터 (실제 DB 연결 필요)",
            "summary": {
                "projects": {
                    "total": 3,
                    "active": 2,
                    "completed": 1
                },
                "tasks": {
                    "total": 5,
                    "completed": 2,
                    "in_progress": 2,
                    "pending": 1
                },
                "users": {
                    "total": 4
                }
            },
            "recent_projects": [
                {
                    "id": 1,
                    "name": "QMS System Enhancement",
                    "status": "active",
                    "progress": 75
                },
                {
                    "id": 2,
                    "name": "AI Integration Project",
                    "status": "active",
                    "progress": 60
                },
                {
                    "id": 3,
                    "name": "Database Migration",
                    "status": "completed",
                    "progress": 100
                }
            ],
            "recent_tasks": [
                {
                    "id": 1,
                    "title": "Implement GPT4All integration",
                    "status": "completed",
                    "priority": "high"
                },
                {
                    "id": 2,
                    "title": "Create MCP server",
                    "status": "completed",
                    "priority": "high"
                },
                {
                    "id": 3,
                    "title": "Build offline packages",
                    "status": "in_progress",
                    "priority": "medium"
                },
                {
                    "id": 4,
                    "title": "Write documentation",
                    "status": "in_progress",
                    "priority": "medium"
                },
                {
                    "id": 5,
                    "title": "Setup HTTPS",
                    "status": "pending",
                    "priority": "low"
                }
            ],
            "database": "rpmt.db (샘플 데이터)"
        }


def get_svit_issues(status: Optional[str] = None) -> Dict[str, Any]:
    """
    SVIT 데이터베이스의 이슈를 정리하여 반환합니다.
    
    Args:
        status: 필터링할 상태 (optional): 'open', 'in_progress', 'closed'
    
    Returns:
        이슈 목록 및 통계 정보
    """
    try:
        if not os.path.exists(SVIT_DB):
            # Return sample data when database doesn't exist
            return {
                "note": "샘플 데이터 (실제 DB 연결 필요)",
                "issues": [
                    {
                        "id": 1,
                        "title": "Login authentication error",
                        "description": "사용자가 로그인 시 인증 오류 발생",
                        "status": "open",
                        "priority": "high",
                        "assigned_to": "Dev Team",
                        "created": "2024-01-10",
                        "updated": "2024-01-15"
                    },
                    {
                        "id": 2,
                        "title": "Report generation slow",
                        "description": "대용량 리포트 생성 시 성능 저하",
                        "status": "in_progress",
                        "priority": "medium",
                        "assigned_to": "Performance Team",
                        "created": "2024-01-12",
                        "updated": "2024-01-20"
                    },
                    {
                        "id": 3,
                        "title": "UI alignment issues",
                        "description": "특정 해상도에서 UI 정렬 문제",
                        "status": "open",
                        "priority": "low",
                        "assigned_to": "Frontend Team",
                        "created": "2024-01-14",
                        "updated": "2024-01-16"
                    },
                    {
                        "id": 4,
                        "title": "Database connection timeout",
                        "description": "피크 시간대 DB 연결 타임아웃",
                        "status": "closed",
                        "priority": "critical",
                        "assigned_to": "Backend Team",
                        "created": "2024-01-05",
                        "updated": "2024-01-18"
                    },
                    {
                        "id": 5,
                        "title": "Email notification not sent",
                        "description": "일부 사용자에게 알림 이메일 미발송",
                        "status": "in_progress",
                        "priority": "medium",
                        "assigned_to": "Backend Team",
                        "created": "2024-01-16",
                        "updated": "2024-01-22"
                    }
                ],
                "total": 5,
                "statistics": {
                    "by_status": {
                        "open": 2,
                        "in_progress": 2,
                        "closed": 1
                    },
                    "by_priority": {
                        "critical": 1,
                        "high": 1,
                        "medium": 2,
                        "low": 1
                    }
                },
                "database": "svit.db (샘플 데이터)"
            }
        
        conn = sqlite3.connect(SVIT_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Build query with optional status filter
        query = """
            SELECT 
                id, title, description, status, 
                priority, assigned_to, created_at, updated_at
            FROM issues
        """
        params = []
        
        if status:
            query += " WHERE status = ?"
            params.append(status)
        
        query += " ORDER BY CASE priority WHEN 'critical' THEN 1 WHEN 'high' THEN 2 WHEN 'medium' THEN 3 WHEN 'low' THEN 4 END, created_at DESC"
        
        cursor.execute(query, params)
        
        issues = []
        for row in cursor.fetchall():
            issues.append({
                "id": row["id"],
                "title": row["title"],
                "description": row["description"],
                "status": row["status"],
                "priority": row["priority"],
                "assigned_to": row["assigned_to"],
                "created": row["created_at"],
                "updated": row["updated_at"]
            })
        
        # Get statistics
        cursor.execute("SELECT status, COUNT(*) as count FROM issues GROUP BY status")
        status_counts = {row["status"]: row["count"] for row in cursor.fetchall()}
        
        cursor.execute("SELECT priority, COUNT(*) as count FROM issues GROUP BY priority")
        priority_counts = {row["priority"]: row["count"] for row in cursor.fetchall()}
        
        conn.close()
        
        return {
            "issues": issues,
            "total": len(issues),
            "statistics": {
                "by_status": status_counts,
                "by_priority": priority_counts
            },
            "database": "svit.db",
            "query_time": datetime.now().isoformat()
        }
        
    except sqlite3.Error as e:
        # Return sample data
        return {
            "note": "샘플 데이터 (실제 DB 연결 필요)",
            "issues": [
                {
                    "id": 1,
                    "title": "Login authentication error",
                    "description": "사용자가 로그인 시 인증 오류 발생",
                    "status": "open",
                    "priority": "high",
                    "assigned_to": "Dev Team",
                    "created": "2024-01-10",
                    "updated": "2024-01-15"
                },
                {
                    "id": 2,
                    "title": "Report generation slow",
                    "description": "대용량 리포트 생성 시 성능 저하",
                    "status": "in_progress",
                    "priority": "medium",
                    "assigned_to": "Performance Team",
                    "created": "2024-01-12",
                    "updated": "2024-01-20"
                },
                {
                    "id": 3,
                    "title": "UI alignment issues",
                    "description": "특정 해상도에서 UI 정렬 문제",
                    "status": "open",
                    "priority": "low",
                    "assigned_to": "Frontend Team",
                    "created": "2024-01-14",
                    "updated": "2024-01-16"
                },
                {
                    "id": 4,
                    "title": "Database connection timeout",
                    "description": "피크 시간대 DB 연결 타임아웃",
                    "status": "closed",
                    "priority": "critical",
                    "assigned_to": "Backend Team",
                    "created": "2024-01-05",
                    "updated": "2024-01-18"
                },
                {
                    "id": 5,
                    "title": "Email notification not sent",
                    "description": "일부 사용자에게 알림 이메일 미발송",
                    "status": "in_progress",
                    "priority": "medium",
                    "assigned_to": "Backend Team",
                    "created": "2024-01-16",
                    "updated": "2024-01-22"
                }
            ],
            "total": 5,
            "statistics": {
                "by_status": {
                    "open": 2,
                    "in_progress": 2,
                    "closed": 1
                },
                "by_priority": {
                    "critical": 1,
                    "high": 1,
                    "medium": 2,
                    "low": 1
                }
            },
            "database": "svit.db (샘플 데이터)"
        }


if __name__ == "__main__":
    print("=" * 60)
    print("QMS Extended MCP Tools - Database Query Demo")
    print("=" * 60)
    print()
    
    # Test CITS customers
    print("1. CITS 고객 조회")
    print("-" * 60)
    result = get_cits_customers()
    if "note" in result:
        print(f"[{result.get('note', '샘플 데이터')}]")
    print(f"총 {result['total']}명의 고객이 등록되어 있습니다:")
    for customer in result["customers"]:
        print(f"  - {customer['company']}")
        print(f"    담당자: {customer['contact']}")
        print(f"    이메일: {customer['email']}")
        print()
    
    print()
    print("2. RPMT DB 요약")
    print("-" * 60)
    result = get_rpmt_summary()
    if "note" in result:
        print(f"[{result.get('note', '샘플 데이터')}]")
    if "error" in result:
        print(f"오류: {result['error']}")
    elif "summary" in result:
        summary = result["summary"]
        print(f"프로젝트: {summary['projects']['total']}개 (활성 {summary['projects']['active']}개)")
        print(f"태스크: {summary['tasks']['total']}개 (완료 {summary['tasks']['completed']}개)")
        print(f"사용자: {summary['users']['total']}명")
        print()
        print("최근 프로젝트:")
        for proj in result["recent_projects"]:
            print(f"  - {proj['name']} ({proj['progress']}%)")
    
    print()
    print("3. SVIT 이슈 정리")
    print("-" * 60)
    result = get_svit_issues()
    if "note" in result:
        print(f"[{result.get('note', '샘플 데이터')}]")
    if "error" in result:
        print(f"오류: {result['error']}")
    elif "statistics" in result:
        stats = result["statistics"]
        print(f"전체 이슈: {result['total']}건")
        print(f"상태별: Open {stats['by_status'].get('open', 0)}건, "
              f"In Progress {stats['by_status'].get('in_progress', 0)}건, "
              f"Closed {stats['by_status'].get('closed', 0)}건")
        print()
        print("이슈 목록:")
        for issue in result["issues"]:
            priority_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
            icon = priority_icon.get(issue["priority"], "⚪")
            print(f"  {icon} [{issue['priority'].upper()}] {issue['title']}")
            print(f"     상태: {issue['status']} | 담당: {issue['assigned_to']}")
