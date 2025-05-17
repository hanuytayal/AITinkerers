import { Board } from './types';

export const initialData: Board = {
  tasks: {
    'task-1': { 
      id: 'task-1', 
      title: 'Create login page', 
      knowledgeLinks: [
        'https://reactjs.org/docs/hooks-reference.html',
        'https://reactrouter.com/docs/en/v6/getting-started/overview'
      ],
      description: 'Implement authentication form with email and password fields, validation, and error handling', 
      priority: 'high',
      status: 'To Do',
      assignee: 'Human',
      dueDate: '2025-06-01' 
    },
    'task-2': { 
      id: 'task-2', 
      title: 'Design dashboard', 
      knowledgeLinks: [
        'https://material-ui.com/components/grid/',
        'https://www.figma.com/resource-library/dashboard-ui-kit/'
      ],
      description: 'Create mockups for main dashboard with user metrics, recent activity, and navigation', 
      priority: 'medium',
      status: 'To Do',
      assignee: 'Human',
      dueDate: '2025-05-25'
    },
    'task-3': { 
      id: 'task-3', 
      title: 'API integration', 
      knowledgeLinks: [
        'https://axios-http.com/docs/intro',
        'https://tanstack.com/query/latest/docs/react/overview'
      ],
      description: 'Connect frontend to backend services using REST API endpoints', 
      priority: 'high',
      status: 'In Progress',
      assignee: 'AI',
      dueDate: '2025-05-30'
    },
    'task-4': { 
      id: 'task-4', 
      title: 'Write tests', 
      knowledgeLinks: [
        'https://jestjs.io/docs/getting-started',
        'https://testing-library.com/docs/react-testing-library/intro/'
      ],
      description: 'Create unit tests for all React components to ensure proper functionality', 
      priority: 'medium',
      status: 'In Progress',
      assignee: 'AI',
      dueDate: '2025-06-10'
    },
    'task-5': { 
      id: 'task-5', 
      title: 'Optimize performance', 
      knowledgeLinks: [
        'https://web.dev/articles/code-splitting-suspense',
        'https://reactjs.org/docs/optimizing-performance.html'
      ],
      description: 'Improve loading times by implementing lazy loading and code splitting', 
      priority: 'low',
      status: 'Done',
      assignee: 'Human',
      dueDate: '2025-05-15'
    },
  },
  columns: {
    'column-1': {
      id: 'column-1',
      title: 'To Do',
      taskIds: ['task-1', 'task-2'],
    },
    'column-2': {
      id: 'column-2',
      title: 'In Progress',
      taskIds: ['task-3', 'task-4'],
    },
    'column-3': {
      id: 'column-3',
      title: 'Done',
      taskIds: ['task-5'],
    },
  },
  columnOrder: ['column-1', 'column-2', 'column-3'],
}; 