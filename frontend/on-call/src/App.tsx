import React from 'react';
import styled from 'styled-components';
import './App.css';
import Header from './components/Header';
import TaskList from './components/TaskList';

const Container = styled.div`
  display: flex;
  flex-direction: column;
  height: 100vh;
`;

const Content = styled.div`
  flex-grow: 1;
  overflow: auto;
`;

const PageHeader = styled.div`
  padding: 20px;
  background-color: #f4f5f7;
  border-bottom: 1px solid #dfe1e6;
`;

const Title = styled.h1`
  margin: 0;
  font-size: 24px;
`;

function App() {
  return (
    <Container>
      <Header />
      <Content>
        <PageHeader>
          <Title>Task List</Title>
        </PageHeader>
        <TaskList />
      </Content>
    </Container>
  );
}

export default App;
