import uuid
from datetime import datetime
import os
import random
import time
import re

class KnowledgeBaseAgent:
    """Agent that augments tickets with knowledge base information"""
    
    def __init__(self):
        """Initialize the knowledge base agent"""
        # Get the absolute path to the data/playbooks directory
        self.knowledge_base_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'playbooks')
        self.knowledge_base = []
        
        # Scan and load actual playbooks from the directory
        self._load_playbooks()
    
    def _load_playbooks(self):
        """Load playbooks from the knowledge base directory"""
        try:
            if os.path.exists(self.knowledge_base_path):
                for filename in os.listdir(self.knowledge_base_path):
                    if filename.endswith('.md'):
                        playbook_path = os.path.join(self.knowledge_base_path, filename)
                        kb_entry = self._parse_playbook(playbook_path, filename)
                        if kb_entry:
                            self.knowledge_base.append(kb_entry)
            
            # If no playbooks found or error, add placeholder playbooks
            if not self.knowledge_base:
                print("Warning: No playbooks found in directory. Using placeholder data.")
                self._add_placeholder_playbooks()
        except Exception as e:
            print(f"Error loading playbooks: {e}")
            self._add_placeholder_playbooks()
    
    def _parse_playbook(self, playbook_path, filename):
        """Parse a playbook file to extract metadata and content"""
        try:
            with open(playbook_path, 'r') as file:
                content = file.read()
                
                # Extract title from metadata or filename
                title_match = re.search(r'Title:\s*(.+)', content)
                title = title_match.group(1) if title_match else filename.replace('.md', '').replace('-', ' ').title()
                
                # Extract a summary from the overview section
                overview_match = re.search(r'## Overview\s*\n(.*?)\n\s*---', content, re.DOTALL)
                summary = overview_match.group(1).strip() if overview_match else "This playbook provides troubleshooting guidance."
                
                # Extract tags from filename and content
                tags = []
                # Add tags from filename
                for tag in filename.replace('.md', '').split('-'):
                    if tag.strip():
                        tags.append(tag.strip().lower())
                
                # Look for specific keywords in the content for additional tags
                keywords = ['memory', 'cpu', 'disk', 'network', 'database', 'api', 'error', 'timeout']
                for keyword in keywords:
                    if keyword.lower() in content.lower() and keyword.lower() not in tags:
                        tags.append(keyword.lower())
                
                # Format the link to use @data notation
                link = f"@AITinkerers/data/playbooks/{filename}"
                
                return {
                    "id": f"kb-{filename.replace('.md', '')}",
                    "title": title,
                    "content": summary,
                    "full_content": content,
                    "link": link,
                    "tags": tags
                }
        except Exception as e:
            print(f"Error parsing playbook {filename}: {e}")
            return None
    
    def _add_placeholder_playbooks(self):
        """Add placeholder playbook entries when actual files can't be loaded"""
        self.knowledge_base = [
            {
                "id": "kb-001",
                "title": "Database Connection Issues Playbook",
                "content": "Common database connection issues can be resolved by checking connection pools, database health, and network connectivity.",
                "link": "@AITinkerers/data/playbooks/db-connection-playbook.md",
                "tags": ["database", "connection", "timeout"]
            },
            {
                "id": "kb-002",
                "title": "Memory Leak Debugging Guide",
                "content": "Memory leaks can be identified through heap dumps and memory profiling. Check for unclosed resources and large object allocations.",
                "link": "@AITinkerers/data/playbooks/memory-leak-guide.md",
                "tags": ["memory", "leak", "OOM", "out of memory"]
            },
            {
                "id": "kb-003",
                "title": "API Gateway Troubleshooting Steps",
                "content": "API Gateway issues often relate to routing, authentication, or rate limiting. Check logs for 4xx and 5xx errors to pinpoint the source.",
                "link": "@AITinkerers/data/playbooks/api-gateway-troubleshooting.md",
                "tags": ["API", "gateway", "routing", "auth"]
            },
            {
                "id": "kb-004",
                "title": "Microservice Dependency Resolution",
                "content": "When services depend on each other, check health endpoints, circuit breakers, and retry mechanisms to ensure resilient communication.",
                "link": "@AITinkerers/data/playbooks/microservice-dependencies.md",
                "tags": ["microservice", "dependency", "circuit breaker"]
            }
        ]
    
    def search_knowledge_base(self, ticket):
        """
        Search knowledge base for relevant information based on the ticket
        
        Args:
            ticket (dict): The ticket to search knowledge for
            
        Returns:
            list: Relevant knowledge base entries
        """
        # Simulate search delay
        time.sleep(0.5)
        
        # Extract search terms from the ticket
        search_terms = []
        
        # Add terms from title and description
        if "title" in ticket:
            search_terms.extend(ticket["title"].lower().split())
        if "description" in ticket:
            search_terms.extend(ticket["description"].lower().split())
        if "issue" in ticket:
            issue = ticket["issue"]
            if "issue_type" in issue:
                search_terms.extend(issue["issue_type"].lower().split())
            if "service" in issue:
                search_terms.extend(issue["service"].lower().split())
        
        # Filter out common words and short terms
        filtered_terms = [term for term in search_terms if len(term) > 3 and term not in ["the", "and", "for", "with", "this", "that"]]
        
        # Find relevant knowledge base entries
        relevant_entries = []
        for entry in self.knowledge_base:
            match_score = 0
            
            # Check for tag matches
            for tag in entry.get("tags", []):
                if any(term in tag or tag in term for term in filtered_terms):
                    match_score += 2
            
            # Check for title matches
            title_lower = entry.get("title", "").lower()
            for term in filtered_terms:
                if term in title_lower:
                    match_score += 1
            
            # Check for content matches
            content_lower = entry.get("content", "").lower()
            for term in filtered_terms:
                if term in content_lower:
                    match_score += 0.5
            
            # Add entries with matches
            if match_score > 0:
                entry_copy = entry.copy()
                entry_copy["match_score"] = match_score
                relevant_entries.append(entry_copy)
        
        # If no relevant entries found, return a random entry
        if not relevant_entries and self.knowledge_base:
            return [random.choice(self.knowledge_base)]
        
        # Sort by match score and return top results (max 2)
        relevant_entries.sort(key=lambda x: x.get("match_score", 0), reverse=True)
        return relevant_entries[:2]


class TicketService:
    """Service to handle creating tickets for oncall engineers"""
    
    def __init__(self):
        """Initialize the ticket service"""
        # In a real implementation, this might connect to a ticketing system API
        self.tickets = []
        
        # Add virtual AI oncall agent
        self.ai_agent = {
            "id": "ai-oncall-001",
            "name": "AI Oncall Agent",
            "team": "Automated Response"
        }
        
        # Initialize knowledge base agent
        self.knowledge_agent = KnowledgeBaseAgent()
        
        # Regular oncall engineers (kept for reference but not used for assignments)
        self.oncall_engineers = [
            {"id": "eng-001", "name": "Alice Smith", "team": "Backend"},
            {"id": "eng-002", "name": "Bob Johnson", "team": "Infrastructure"},
            {"id": "eng-003", "name": "Charlie Davis", "team": "Frontend"},
            {"id": "eng-004", "name": "Diana Lee", "team": "Database"},
            {"id": "eng-005", "name": "Evan Wilson", "team": "Security"}
        ]
    
    def create_ticket(self, issue):
        """
        Create a ticket for an issue
        
        Args:
            issue (dict): The issue to create a ticket for
            
        Returns:
            dict: The created ticket
        """
        # Always assign to AI oncall agent
        assigned_engineer = self.ai_agent
        
        # Generate ticket ID
        ticket_id = f"TICKET-{str(uuid.uuid4())[:8]}"
        
        # Create ticket
        ticket = {
            "id": ticket_id,
            "title": f"{issue['severity']} {issue['issue_type']} in {issue['service']}",
            "description": issue['description'],
            "status": "Open",
            "created_at": datetime.now().isoformat(),
            "assigned_to": assigned_engineer,
            "issue": issue,
            "priority": self._map_severity_to_priority(issue['severity'])
        }
        
        # Store ticket (in a real system, this would be sent to an API)
        self.tickets.append(ticket)
        
        # Augment ticket with knowledge base information
        self.augment_ticket_with_knowledge(ticket)
        
        return ticket
    
    def augment_ticket_with_knowledge(self, ticket):
        """
        Augment a ticket with knowledge base information from the knowledge agent
        
        Args:
            ticket (dict): The ticket to augment
        """
        # Find relevant knowledge base entries for this ticket
        knowledge_entries = self.knowledge_agent.search_knowledge_base(ticket)
        
        # Add knowledge base entries to the ticket
        ticket["knowledge_base"] = knowledge_entries
        
        return ticket
    
    def _assign_engineer(self, service):
        """
        This method is kept for backward compatibility but is no longer used.
        All tickets are now assigned to the AI oncall agent.
        """
        return self.ai_agent
    
    def _map_severity_to_priority(self, severity):
        """Map severity to priority level"""
        priority_map = {
            "Critical": "P0 - Immediate",
            "High": "P1 - High",
            "Medium": "P2 - Medium",
            "Low": "P3 - Low"
        }
        return priority_map.get(severity, "P2 - Medium")
    
    def get_tickets(self):
        """Get all tickets"""
        return self.tickets
    
    def get_ticket(self, ticket_id):
        """Get a specific ticket by ID"""
        for ticket in self.tickets:
            if ticket['id'] == ticket_id:
                return ticket
        return None 