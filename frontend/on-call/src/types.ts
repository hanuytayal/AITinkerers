export interface Task {
  id: string;
  title: string;
  description: string;
  summary: string;
  priority: "low" | "medium" | "high";
  status: "To Do" | "In Progress" | "Done";
  assignee: "AI" | "Human" | undefined;
  dueDate?: string;
}

export interface Column {
  id: string;
  title: string;
  taskIds: string[];
}

export interface Board {
  tasks: {
    [key: string]: Task;
  };
  columns: {
    [key: string]: Column;
  };
  columnOrder: string[];
}
