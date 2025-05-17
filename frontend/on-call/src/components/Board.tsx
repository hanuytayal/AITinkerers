import React, { useState } from 'react';
import styled from 'styled-components';
import { DragDropContext, DropResult } from 'react-beautiful-dnd';
import Column from './Column';
import { initialData } from '../data';
import { Board as BoardType } from '../types';

const Container = styled.div`
  display: flex;
  padding: 20px;
  overflow-x: auto;
  min-height: 80vh;
  background-color: #fbfbfc;
`;

const Board: React.FC = () => {
  const [board, setBoard] = useState<BoardType>(initialData);

  const onDragEnd = (result: DropResult) => {
    const { destination, source, draggableId } = result;

    // If there's no destination, we don't need to do anything
    if (!destination) {
      return;
    }

    // If the location hasn't changed, we don't need to do anything
    if (
      destination.droppableId === source.droppableId &&
      destination.index === source.index
    ) {
      return;
    }

    // Moving within the same column
    if (source.droppableId === destination.droppableId) {
      const column = board.columns[source.droppableId];
      const newTaskIds = Array.from(column.taskIds);
      newTaskIds.splice(source.index, 1);
      newTaskIds.splice(destination.index, 0, draggableId);

      const newColumn = {
        ...column,
        taskIds: newTaskIds,
      };

      const newBoard = {
        ...board,
        columns: {
          ...board.columns,
          [newColumn.id]: newColumn,
        },
      };

      setBoard(newBoard);
      return;
    }

    // Moving from one column to another
    const startColumn = board.columns[source.droppableId];
    const finishColumn = board.columns[destination.droppableId];
    
    const startTaskIds = Array.from(startColumn.taskIds);
    startTaskIds.splice(source.index, 1);
    
    const newStartColumn = {
      ...startColumn,
      taskIds: startTaskIds,
    };

    const finishTaskIds = Array.from(finishColumn.taskIds);
    finishTaskIds.splice(destination.index, 0, draggableId);
    
    const newFinishColumn = {
      ...finishColumn,
      taskIds: finishTaskIds,
    };

    const newBoard = {
      ...board,
      columns: {
        ...board.columns,
        [newStartColumn.id]: newStartColumn,
        [newFinishColumn.id]: newFinishColumn,
      },
    };

    setBoard(newBoard);
  };

  return (
    <DragDropContext onDragEnd={onDragEnd}>
      <Container>
        {board.columnOrder.map(columnId => {
          const column = board.columns[columnId];
          const tasks = column.taskIds.map(taskId => board.tasks[taskId]);

          return <Column key={column.id} column={column} tasks={tasks} />;
        })}
      </Container>
    </DragDropContext>
  );
};

export default Board; 