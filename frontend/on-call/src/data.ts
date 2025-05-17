import { Board } from './types';

export const initialData: Board = {
  tasks: {
    'task-1': { id: 'task-1', title: 'Create login page', description: 'Implement authentication form', priority: 'high' },
    'task-2': { id: 'task-2', title: 'Design dashboard', description: 'Create mockups for main dashboard', priority: 'medium' },
    'task-3': { id: 'task-3', title: 'API integration', description: 'Connect frontend to backend services', priority: 'high' },
    'task-4': { id: 'task-4', title: 'Write tests', description: 'Create unit tests for components', priority: 'medium' },
    'task-5': { id: 'task-5', title: 'Optimize performance', description: 'Improve loading times', priority: 'low' },
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