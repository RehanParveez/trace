import {createBrowserRouter, Navigate,
} from "react-router-dom";
import { HomePage } from "../modules/home/HomePage";
import {LoginPage, RegisterPage, ForgotPasswordPage, ResetPasswordPage, VerifyEmailPage, ProfilePage,
} from "../modules/identity/pages";
import {ProtectedRoute, PublicOnlyRoute,
} from "../modules/identity";
import { OrganizationShell, OrganizationPage, OrganizationMembersPage, OrganizationMemberDetailPage, OrganizationRolesPage, OrganizationRoleDetailPage, OrganizationInvitationsPage,
} from "../modules/organizations";
import { AppErrorBoundary } from "../shared/components/AppErrorBoundary";
import {SubscriptionPage,
} from "../modules/subscriptions";
import {ProjectsPage, ProjectDetailPage,
} from "../modules/projects";
import { MaterialLibraryPage } from "../modules/drawings_boq";
import { SitePhotosPage, WhatsAppSettingsPage } from "../modules/whatsapp";
import { ProgressClaimsReviewPage } from "../modules/verification";

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
    errorElement: <AppErrorBoundary />,
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

      {
       path: "subscription",
       element: <OrganizationShell />,
       children: [
        {
         index: true,
         element: <SubscriptionPage />,
        },
      ],
    },

      {
       path: "organization",
       element: <OrganizationShell />,
       children: [
    {
      index: true,
      element: <OrganizationPage />,
    },

    {
      path: "members",
      element: <OrganizationMembersPage />,
    },

    {
      path: "members/:userId",
      element: <OrganizationMemberDetailPage />,
    },

    {
      path: "roles",
      element: <OrganizationRolesPage />,
    },

    {
      path: "roles/:roleId",
      element: <OrganizationRoleDetailPage />,
    },

    {
      path: "invitations",
      element: <OrganizationInvitationsPage />,
    },
  ],
},

{
  path: "projects",
  element: <OrganizationShell />,
  children: [
    {
      index: true,
      element: <ProjectsPage />,
    },

    {
      path: ":projectId",
      element: <ProjectDetailPage />,
    },
  ],
},

{
  path: "drawings_boq",
  element: <OrganizationShell />,
  children: [
    {
      index: true,
      element: <MaterialLibraryPage />,
    },
   ],
  },

  {
  path: "site-photos",
  element: <OrganizationShell />,
  children: [
    {
      index: true,
      element: <SitePhotosPage />,
    },
  ],
},

{
  path: "whatsapp-settings",
  element: <OrganizationShell />,
  children: [
    {
      index: true,
      element: <WhatsAppSettingsPage />,
    },
  ],
},

{
  path: "progress-review",
  element: <OrganizationShell />,
  children: [
    {
      index: true,
      element: <ProgressClaimsReviewPage />,
    },
  ],
},

  ],
 },
]);