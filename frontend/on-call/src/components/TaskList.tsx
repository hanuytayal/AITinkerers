import React, { useState } from 'react';
import styled from 'styled-components';
import { initialData } from '../data';
import { Task as TaskType } from '../types';
import TaskDetailModal from './TaskDetailModal';

const Container = styled.div`
  padding: 20px;
  background-color: #fbfbfc;
`;

const Table = styled.table`
  width: 100%;
  border-collapse: collapse;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  border-radius: 4px;
  overflow: hidden;
`;

const TableHead = styled.thead`
  background-color: #f4f5f7;
`;

const TableRow = styled.tr`
  border-bottom: 1px solid #dfe1e6;
  &:hover {
    background-color: #f8f9fa;
  }
  cursor: pointer;
`;

const HeaderRow = styled(TableRow)`
  &:hover {
    background-color: #f4f5f7;
  }
  cursor: default;
`;

const TableHeader = styled.th`
  text-align: left;
  padding: 12px 16px;
  font-weight: 600;
  color: #172b4d;
  font-size: 14px;
`;

const TableCell = styled.td`
  padding: 12px 16px;
  font-size: 14px;
  color: #172b4d;
`;

const Status = styled.span<{ status: 'To Do' | 'In Progress' | 'Done' }>`
  padding: 3px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  background-color: ${props => {
    switch (props.status) {
      case 'To Do':
        return '#dfe1e6';
      case 'In Progress':
        return '#deebff';
      case 'Done':
        return '#e3fcef';
      default:
        return '#dfe1e6';
    }
  }};
  color: ${props => {
    switch (props.status) {
      case 'To Do':
        return '#42526e';
      case 'In Progress':
        return '#0052cc';
      case 'Done':
        return '#006644';
      default:
        return '#42526e';
    }
  }};
`;

const Assignee = styled.span<{ assignee: 'AI' | 'Human' | undefined }>`
  padding: 3px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  background-color: ${props => 
    props.assignee === 'AI' ? '#ffe2d9' : 
    props.assignee === 'Human' ? '#d3f1fd' : '#dfe1e6'};
  color: ${props => 
    props.assignee === 'AI' ? '#b93800' : 
    props.assignee === 'Human' ? '#0065b3' : '#42526e'};
`;

const LinkCell = styled.div`
  display: flex;
  flex-direction: column;
  gap: 4px;
`;

const LinkIndicator = styled.div`
  font-size: 12px;
  color: #0052cc;
  display: flex;
  align-items: center;
  gap: 4px;
`;

const LinkIcon = styled.span`
  font-size: 14px;
`;

const formatDate = (dateString?: string) => {
  if (!dateString) return '-';
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
};

const TaskList: React.FC = () => {
  const [selectedTask, setSelectedTask] = useState<TaskType | null>(null);
  
  // Convert tasks object to array
  const tasks = Object.values(initialData.tasks);

  const handleTaskClick = (task: TaskType) => {
    setSelectedTask(task);
  };

  const handleCloseModal = () => {
    setSelectedTask(null);
  };

  return (
    <Container>
      <Table>
        <TableHead>
          <HeaderRow>
            <TableHeader>Title</TableHeader>
            <TableHeader>Knowledge Links</TableHeader>
            <TableHeader>Status</TableHeader>
            <TableHeader>Assignee</TableHeader>
            <TableHeader>Due Date</TableHeader>
            <TableHeader>Priority</TableHeader>
          </HeaderRow>
        </TableHead>
        <tbody>
          {tasks.map(task => (
            <TableRow key={task.id} onClick={() => handleTaskClick(task)}>
              <TableCell>{task.title}</TableCell>
              <TableCell>
                <LinkCell>
                  {task.knowledgeLinks.map((link, index) => (
                    <LinkIndicator key={index}>
                      <LinkIcon>🔗</LinkIcon>
                      Link {index + 1}
                    </LinkIndicator>
                  ))}
                </LinkCell>
              </TableCell>
              <TableCell>
                <Status status={task.status}>{task.status}</Status>
              </TableCell>
              <TableCell>
                <Assignee assignee={task.assignee}>{task.assignee || '-'}</Assignee>
              </TableCell>
              <TableCell>{formatDate(task.dueDate)}</TableCell>
              <TableCell>{task.priority}</TableCell>
            </TableRow>
          ))}
        </tbody>
      </Table>
      
      {selectedTask && (
        <TaskDetailModal task={selectedTask} onClose={handleCloseModal} />
      )}
    </Container>
  );
};

export default TaskList; 