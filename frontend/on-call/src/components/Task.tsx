import React from 'react';
import styled from 'styled-components';
import { Draggable } from 'react-beautiful-dnd';
import { Task as TaskType } from '../types';

interface TaskProps {
  task: TaskType;
  index: number;
}

const Container = styled.div<{ isDragging: boolean }>`
  border: 1px solid lightgrey;
  border-radius: 3px;
  padding: 12px;
  margin-bottom: 8px;
  background-color: ${props => (props.isDragging ? '#e6fcff' : 'white')};
  box-shadow: ${props => (props.isDragging ? '0px 2px 5px rgba(0,0,0,0.2)' : 'none')};
`;

const Title = styled.h3`
  margin: 0 0 8px 0;
  font-size: 16px;
`;

const Description = styled.div`
  margin-bottom: 8px;
  font-size: 14px;
  color: #555;
`;

const Meta = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
`;

const Priority = styled.span<{ priority: 'low' | 'medium' | 'high' }>`
  padding: 2px 6px;
  border-radius: 3px;
  background-color: ${props => {
    switch (props.priority) {
      case 'high':
        return '#ffebe6';
      case 'medium':
        return '#fffae6';
      case 'low':
        return '#e3fcef';
      default:
        return '#f4f5f7';
    }
  }};
  color: ${props => {
    switch (props.priority) {
      case 'high':
        return '#cb2431';
      case 'medium':
        return '#b38600';
      case 'low':
        return '#006644';
      default:
        return '#555';
    }
  }};
`;

const Task: React.FC<TaskProps> = ({ task, index }) => {
  return (
    <Draggable draggableId={task.id} index={index}>
      {(provided, snapshot) => (
        <Container
          {...provided.draggableProps}
          {...provided.dragHandleProps}
          ref={provided.innerRef}
          isDragging={snapshot.isDragging}
        >
          <Title>{task.title}</Title>
          <Description>{task.description}</Description>
          <Meta>
            <Priority priority={task.priority}>
              {task.priority.charAt(0).toUpperCase() + task.priority.slice(1)}
            </Priority>
            {task.assignee && <div>Assignee: {task.assignee}</div>}
          </Meta>
        </Container>
      )}
    </Draggable>
  );
};

export default Task; 