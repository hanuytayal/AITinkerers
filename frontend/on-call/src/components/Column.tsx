import React from "react";
import styled from "styled-components";
import { Droppable } from "react-beautiful-dnd";
import Task from "./Task";
import { Column as ColumnType, Task as TaskType } from "../types";

interface ColumnProps {
  column: ColumnType;
  tasks: TaskType[];
}

const Container = styled.div`
  margin: 8px;
  border: 1px solid lightgrey;
  border-radius: 3px;
  width: 300px;
  display: flex;
  flex-direction: column;
  background-color: #f4f5f7;
`;

const Title = styled.h3`
  padding: 8px;
  font-size: 16px;
  margin: 0;
  border-bottom: 1px solid lightgrey;
  background-color: #e2e4e9;
`;

const TaskList = styled.div<{ isDraggingOver: boolean }>`
  padding: 8px;
  flex-grow: 1;
  min-height: 100px;
  background-color: ${(props) =>
    props.isDraggingOver ? "#e6fcff" : "#f4f5f7"};
  transition: background-color 0.2s ease;
`;

const Column: React.FC<ColumnProps> = ({ column, tasks }) => {
  return (
    <Container>
      <Title>{column.title}</Title>
      <Droppable droppableId={column.id}>
        {(provided, snapshot) => (
          <TaskList
            ref={provided.innerRef}
            {...provided.droppableProps}
            isDraggingOver={snapshot.isDraggingOver}
          >
            {tasks.map((task, index) => (
              <Task key={task.id} task={task} index={index} />
            ))}
            {provided.placeholder}
          </TaskList>
        )}
      </Droppable>
    </Container>
  );
};

export default Column;
