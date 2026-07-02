import { createRouter, createWebHistory } from "vue-router";

import AiChatView from "../views/ai/AiChatView.vue";
import LoginView from "../views/auth/LoginView.vue";
import RegisterView from "../views/auth/RegisterView.vue";
import TermsView from "../views/auth/TermsView.vue";
import ForumPostDetailView from "../views/forum/ForumPostDetailView.vue";
import ForumListView from "../views/forum/ForumListView.vue";
import HomeView from "../views/HomeView.vue";
import LedgerView from "../views/ledger/LedgerView.vue";
import MarketExploreView from "../views/market/MarketExploreView.vue";
import MarketItemDetailView from "../views/market/MarketItemDetailView.vue";
import MarketOrdersView from "../views/market/MarketOrdersView.vue";
import ProjectDetailView from "../views/project/ProjectDetailView.vue";
import ProjectListView from "../views/project/ProjectListView.vue";
import NotificationCenterView from "../views/notification/NotificationCenterView.vue";
import ProfileOverviewView from "../views/profile/ProfileOverviewView.vue";
import ProjectPlaceholderView from "../views/project/ProjectPlaceholderView.vue";

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
