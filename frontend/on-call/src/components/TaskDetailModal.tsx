import React from 'react';
import styled from 'styled-components';
import { Task } from '../types';

interface TaskDetailModalProps {
  task: Task;
  onClose: () => void;
}

const ModalOverlay = styled.div`
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
`;

const ModalContent = styled.div`
  background-color: white;
  border-radius: 5px;
  width: 600px;
  max-width: 90%;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
`;

const ModalHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  border-bottom: 1px solid #dfe1e6;
`;

const ModalTitle = styled.h2`
  margin: 0;
  font-size: 24px;
  color: #172b4d;
`;

const CloseButton = styled.button`
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #6b778c;
  &:hover {
    color: #172b4d;
  }
`;

const ModalBody = styled.div`
  padding: 24px;
`;

const DetailSection = styled.div`
  margin-bottom: 24px;
`;

const DetailLabel = styled.h3`
  margin: 0 0 8px 0;
  font-size: 16px;
  color: #6b778c;
`;

const DetailContent = styled.div`
  font-size: 16px;
  color: #172b4d;
  line-height: 1.5;
`;

const MetaSection = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  padding: 16px 24px;
  background-color: #f4f5f7;
  border-top: 1px solid #dfe1e6;
`;

const MetaItem = styled.div`
  display: flex;
  flex-direction: column;
`;

const MetaLabel = styled.div`
  font-size: 12px;
  color: #6b778c;
  margin-bottom: 4px;
`;

const MetaValue = styled.div`
  font-size: 14px;
  color: #172b4d;
  font-weight: 500;
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

const formatDate = (dateString?: string) => {
  if (!dateString) return '-';
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
};

const TaskDetailModal: React.FC<TaskDetailModalProps> = ({ task, onClose }) => {
  // Close when clicking outside the modal
  const handleOverlayClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  return (
    <ModalOverlay onClick={handleOverlayClick}>
      <ModalContent>
        <ModalHeader>
          <ModalTitle>{task.title}</ModalTitle>
          <CloseButton onClick={onClose}>&times;</CloseButton>
        </ModalHeader>
        <ModalBody>
          <DetailSection>
            <DetailLabel>Description</DetailLabel>
            <DetailContent>{task.description}</DetailContent>
          </DetailSection>
          <DetailSection>
            <DetailLabel>Summary</DetailLabel>
            <DetailContent>{task.summary}</DetailContent>
          </DetailSection>
        </ModalBody>
        <MetaSection>
          <MetaItem>
            <MetaLabel>Assignee</MetaLabel>
            <MetaValue>
              <Assignee assignee={task.assignee}>{task.assignee || '-'}</Assignee>
            </MetaValue>
          </MetaItem>
          <MetaItem>
            <MetaLabel>Status</MetaLabel>
            <MetaValue>
              <Status status={task.status}>{task.status}</Status>
            </MetaValue>
          </MetaItem>
          <MetaItem>
            <MetaLabel>Priority</MetaLabel>
            <MetaValue>{task.priority}</MetaValue>
          </MetaItem>
          <MetaItem>
            <MetaLabel>Due Date</MetaLabel>
            <MetaValue>{formatDate(task.dueDate)}</MetaValue>
          </MetaItem>
        </MetaSection>
      </ModalContent>
    </ModalOverlay>
  );
};

export default TaskDetailModal; 