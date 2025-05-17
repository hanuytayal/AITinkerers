import uuid
from datetime import datetime

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