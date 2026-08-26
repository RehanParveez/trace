import {createBrowserRouter, Navigate,
} from "react-router-dom";
import { HomePage } from "../modules/home/HomePage";
import {LoginPage, RegisterPage, ForgotPasswordPage, ResetPasswordPage, VerifyEmailPage, ProfilePage,
} from "../modules/identity/pages";
import {ProtectedRoute, PublicOnlyRoute,
} from "../modules/identity";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <HomePage />,
  },

  {
    path: "/login",
    element: (
      <PublicOnlyRoute>
        <LoginPage />
      </PublicOnlyRoute>
    ),
  },

  {
    path: "/register",
    element: (
      <PublicOnlyRoute>
        <RegisterPage />
      </PublicOnlyRoute>
    ),
  },

  {
    path: "/forgot-password",
    element: (
      <PublicOnlyRoute>
        <ForgotPasswordPage />
      </PublicOnlyRoute>
    ),
  },

  {
    path: "/reset-password",
    element: (
      <PublicOnlyRoute>
        <ResetPasswordPage />
      </PublicOnlyRoute>
    ),
  },

  {
    path: "/verify-email",
    element: <VerifyEmailPage />,
  },

  {
    path: "/app",
    element: <ProtectedRoute />,
    children: [
      {
        index: true,
        element: (
          <Navigate
            to="/app/profile"
            replace
          />
        ),
      },

      {
        path: "profile",
        element: <ProfilePage />,
      },
    ],
  },
]);