import React, { useState } from "react";
import styled from "styled-components";
import { DragDropContext, DropResult } from "react-beautiful-dnd";
import Column from "./Column";
import { initialData } from "../data";
import { Board as BoardType } from "../types";

const Container = styled.div`
  display: flex;
  padding: 20px;
  overflow-x: auto;
  min-height: 80vh;
  background-color: #fbfbfc;
`;

const Board: React.FC = () => {
  const [board, setBoard] = useState<BoardType>(initialData);

  // Handles reordering tasks within the same column
  const _handleDragInSameColumn = (
    currentBoard: BoardType,
    source: DropResult["source"],
    destination: DropResult["destination"],
    draggableId: string,
  ): BoardType => {
    const column = currentBoard.columns[source.droppableId];
    // Create a new array of task IDs to avoid direct mutation
    const newTaskIds = Array.from(column.taskIds);
    // Remove the draggableId from its original position
    newTaskIds.splice(source.index, 1);
    // Insert the draggableId into its new position
    newTaskIds.splice(destination.index, 0, draggableId);

    // Create an updated column object with the new taskIds order
    const newColumn = {
      ...column, // Spread existing column properties
      taskIds: newTaskIds, // Override with the new taskIds array
    };

    // Create the updated board state
    return {
      ...currentBoard, // Spread existing board properties
      columns: {
        ...currentBoard.columns, // Spread existing columns
        [newColumn.id]: newColumn, // Override the updated column
      },
    };
  };

  // Handles moving tasks between different columns
  const _handleDragToDifferentColumn = (
    currentBoard: BoardType,
    source: DropResult["source"],
    destination: DropResult["destination"],
    draggableId: string,
  ): BoardType => {
    const startColumn = currentBoard.columns[source.droppableId];
    const finishColumn = currentBoard.columns[destination.droppableId];

    // Create new arrays for taskIds for immutable update
    const startTaskIds = Array.from(startColumn.taskIds);
    // Remove the task from the source column
    startTaskIds.splice(source.index, 1);
    const newStartColumn = {
      ...startColumn,
      taskIds: startTaskIds,
    };

    const finishTaskIds = Array.from(finishColumn.taskIds);
    // Add the task to the destination column at the correct position
    finishTaskIds.splice(destination.index, 0, draggableId);
    const newFinishColumn = {
      ...finishColumn,
      taskIds: finishTaskIds,
    };

    // Create the updated board state
    return {
      ...currentBoard,
      columns: {
        ...currentBoard.columns,
        [newStartColumn.id]: newStartColumn, // Updated source column
        [newFinishColumn.id]: newFinishColumn, // Updated destination column
      },
    };
  };

  const onDragEnd = (result: DropResult) => {
    const { destination, source, draggableId } = result;

    // Case 1: Item dropped outside a valid droppable destination
    // No action needed if there's no destination.
    if (!destination) {
      return;
    }

    // Case 2: Item dropped in the same position it started
    // No action needed if the item's location hasn't changed.
    if (
      destination.droppableId === source.droppableId &&
      destination.index === source.index
    ) {
      return;
    }

    // Case 3: Item moved within the same column
    if (source.droppableId === destination.droppableId) {
      const newBoard = _handleDragInSameColumn(
        board,
        source,
        destination,
        draggableId,
      );
      setBoard(newBoard);
      return;
    }

    // Case 4: Item moved to a different column
    const newBoard = _handleDragToDifferentColumn(
      board,
      source,
      destination,
      draggableId,
    );
    setBoard(newBoard);
  };

  return (
    <DragDropContext onDragEnd={onDragEnd}>
      <Container>
        {board.columnOrder.map((columnId) => {
          const column = board.columns[columnId];
          const tasks = column.taskIds.map((taskId) => board.tasks[taskId]);

          return <Column key={column.id} column={column} tasks={tasks} />;
        })}
      </Container>
    </DragDropContext>
  );
};

export default Board;
