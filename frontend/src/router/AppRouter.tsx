import { Route, Routes } from 'react-router-dom';
import AppLayout from '../components/layout/AppLayout';
import SearchPage from '../pages/SearchPage';
import ItemsPage from '../pages/ItemsPage';
import ItemDetailPage from '../pages/ItemDetailPage';
import UsersPage from '../pages/UsersPage';
import UserDetailPage from '../pages/UserDetailPage';
import EvaluationPage from '../pages/EvaluationPage';
import SystemPage from '../pages/SystemPage';
import ActivityPage from '../pages/ActivityPage';
import NotFoundPage from '../pages/NotFoundPage';

export function AppRouter() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<SearchPage />} />
        <Route path="search" element={<SearchPage />} />
        <Route path="items" element={<ItemsPage />} />
        <Route path="items/:itemId" element={<ItemDetailPage />} />
        <Route path="users" element={<UsersPage />} />
        <Route path="users/:userId" element={<UserDetailPage />} />
        <Route path="activity" element={<ActivityPage />} />
        <Route path="evaluation" element={<EvaluationPage />} />
        <Route path="system" element={<SystemPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
