import React from "react";
import styled from "styled-components";

const Container = styled.div`
  background-color: #0052cc;
  color: white;
  padding: 16px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
`;

const Logo = styled.div`
  font-size: 24px;
  font-weight: bold;
`;

const Navigation = styled.div`
  display: flex;
  gap: 20px;
`;

const NavItem = styled.div`
  cursor: pointer;
  padding: 8px 12px;
  border-radius: 3px;
  transition: background-color 0.2s ease;

  &:hover {
    background-color: rgba(255, 255, 255, 0.1);
  }
`;

const Header: React.FC = () => {
  return (
    <Container>
      <Logo>Task Manager</Logo>
      <Navigation>
        <NavItem>Tasks</NavItem>
        <NavItem>Calendar</NavItem>
        <NavItem>Reports</NavItem>
        <NavItem>Settings</NavItem>
      </Navigation>
    </Container>
  );
};

export default Header;
