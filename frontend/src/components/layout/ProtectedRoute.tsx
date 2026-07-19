import { Navigate, Outlet } from "react-router-dom";
import { getAuthToken } from "../../utils/storage";

export function ProtectedRoute() {
  if (!getAuthToken()) {
    return <Navigate to="/login" replace />;
  }
  return <Outlet />;
}
