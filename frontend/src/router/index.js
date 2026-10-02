import { createRouter, createWebHistory } from "vue-router";

// The homepage is where most visits start, so it ships in the main bundle.
// Every other page is its own chunk, downloaded the first time it is visited.
import HomeView from "../views/HomeView.vue";

const AiChatView = () => import("../views/ai/AiChatView.vue");
const LoginView = () => import("../views/auth/LoginView.vue");
const RegisterView = () => import("../views/auth/RegisterView.vue");
const TermsView = () => import("../views/auth/TermsView.vue");
const ForumPostDetailView = () => import("../views/forum/ForumPostDetailView.vue");
const ForumListView = () => import("../views/forum/ForumListView.vue");
const LedgerView = () => import("../views/ledger/LedgerView.vue");
const MarketExploreView = () => import("../views/market/MarketExploreView.vue");
const MarketItemDetailView = () => import("../views/market/MarketItemDetailView.vue");
const MarketOrdersView = () => import("../views/market/MarketOrdersView.vue");
const ProjectDetailView = () => import("../views/project/ProjectDetailView.vue");
const ProjectListView = () => import("../views/project/ProjectListView.vue");
const NotificationCenterView = () => import("../views/notification/NotificationCenterView.vue");
const ProfileOverviewView = () => import("../views/profile/ProfileOverviewView.vue");
// Prototypes for the redesign; not linked from the app.
const ViewfinderLabView = () => import("../views/lab/ViewfinderLabView.vue");

const TOKEN_KEY = "cs_token";

function isAuthenticated() {
  return !!localStorage.getItem(TOKEN_KEY);
}

const routes = [
  {
    path: "/",
    name: "home",
    component: HomeView,
  },
  {
    path: "/ai",
    name: "ai",
    component: AiChatView,
  },
  {
    path: "/start",
    redirect: "/",
  },
  {
    path: "/login",
    name: "login",
    component: LoginView,
  },
  {
    path: "/register",
    name: "register",
    component: RegisterView,
  },
  {
    path: "/terms",
    name: "terms",
    component: TermsView,
  },
  {
    path: "/forum",
    name: "forum",
    component: ForumListView,
  },
  {
    path: "/forum/posts/:id",
    name: "forum-post-detail",
    component: ForumPostDetailView,
  },
  {
    path: "/project",
    name: "project",
    component: ProjectListView,
  },
  {
    path: "/project/:id",
    name: "project-detail",
    component: ProjectDetailView,
  },
  {
    path: "/market",
    name: "market",
    component: MarketExploreView,
  },
  {
    path: "/market/orders",
    name: "market-orders",
    component: MarketOrdersView,
  },
  {
    path: "/market/items/:id",
    name: "market-item",
    component: MarketItemDetailView,
  },
  {
    path: "/ledger",
    name: "ledger",
    component: LedgerView,
    meta: { requiresAuth: true },
  },
  {
    path: "/notification",
    name: "notification",
    component: NotificationCenterView,
  },
  {
    path: "/profile",
    name: "profile",
    component: ProfileOverviewView,
    meta: { requiresAuth: true },
  },
  {
    path: "/lab/viewfinder",
    name: "lab-viewfinder",
    component: ViewfinderLabView,
  },
  {
    path: "/:pathMatch(.*)*",
    redirect: "/",
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach((to) => {
  if (to.meta.requiresAuth && !isAuthenticated()) {
    return { name: "login", query: { redirect: to.fullPath } };
  }
});

export default router;
