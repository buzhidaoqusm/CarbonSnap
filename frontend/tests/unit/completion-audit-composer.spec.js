import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import CompletionAuditComposer from "../../src/components/ai/CompletionAuditComposer.vue";

describe("CompletionAuditComposer", () => {
  it("shows retryable audit state for failed cases", () => {
    const wrapper = mount(CompletionAuditComposer, {
      props: {
        caseData: {
          waste_type_predicted: "plastic bottle",
          expected_carbon_points: 3,
          latest_audit_attempt_no: 1,
          status: "audit_failed",
        },
      },
    });

    expect(wrapper.text()).toContain("Upload Completion Photo");
    expect(wrapper.text()).toContain("Retryable");
    expect(wrapper.text()).toContain("plastic bottle");
    expect(wrapper.text()).toContain("The last audit was not approved");
  });

  it("locks upload controls and shows feedback after approval", () => {
    const wrapper = mount(CompletionAuditComposer, {
      props: {
        caseData: {
          waste_type_predicted: "glass bottle",
          expected_carbon_points: 5,
          latest_audit_attempt_no: 2,
          status: "audit_passed",
        },
        locked: true,
        submittedImageUrl: "/api/uploads/recycling-audit/example.jpg",
        feedback: "Audit passed. Your recycling case has been verified.",
      },
    });

    expect(wrapper.text()).toContain("Verified");
    expect(wrapper.find('input[type="file"]').exists()).toBe(false);
    expect(wrapper.find("textarea").exists()).toBe(false);
    expect(wrapper.text()).toContain("AI feedback");
    expect(wrapper.text()).toContain("Audit passed. Your recycling case has been verified.");
    expect(wrapper.text()).toContain("2");
  });

  it("lets the user review previous audit attempts after verification", async () => {
    const wrapper = mount(CompletionAuditComposer, {
      props: {
        caseData: {
          waste_type_predicted: "power bank",
          expected_carbon_points: 5,
          latest_audit_attempt_no: 2,
          status: "audit_passed",
        },
        attempts: [
          {
            id: 1,
            attempt_no: 1,
            audit_result: "unclear",
            audit_reason: "The disposal path is not clear enough.",
            audit_image_url: "/api/uploads/recycling-audit/attempt-1.jpg",
          },
          {
            id: 2,
            attempt_no: 2,
            audit_result: "passed",
            audit_reason: "The item is at the correct collection point.",
            audit_image_url: "/api/uploads/recycling-audit/attempt-2.jpg",
          },
        ],
        locked: true,
        submittedImageUrl: "/api/uploads/recycling-audit/attempt-2.jpg",
        feedback: "Audit passed. Your recycling case has been verified, and 5 points were awarded.",
      },
    });

    expect(wrapper.text()).toContain("2/2");
    expect(wrapper.text()).toContain("Attempts");
    expect(wrapper.text()).toContain("Audit passed. Your recycling case has been verified, and 5 points were awarded.");

    const buttons = wrapper.findAll(".completion-audit-composer__attempt-button");
    await buttons[0].trigger("click");

    expect(wrapper.text()).toContain("1/2");
    expect(wrapper.text()).toContain("Attempt 1 · Unclear");
    expect(wrapper.text()).toContain("Audit unclear. The disposal path is not clear enough.");
    expect(wrapper.find(".completion-audit-composer__preview-image").attributes("src")).toBe(
      "/api/uploads/recycling-audit/attempt-1.jpg",
    );
  });

  it("deduplicates repeated attempts that share the same attempt number", () => {
    const wrapper = mount(CompletionAuditComposer, {
      props: {
        caseData: {
          waste_type_predicted: "power bank",
          expected_carbon_points: 4,
          latest_audit_attempt_no: 2,
          status: "audit_passed",
        },
        attempts: [
          {
            id: 2,
            attempt_no: 1,
            audit_result: "unclear",
            audit_reason: "The disposal path is not clear enough.",
            audit_image_url: "/api/uploads/recycling-audit/attempt-1.jpg",
          },
          {
            id: 3,
            attempt_no: 2,
            audit_result: "passed",
            audit_reason: "The photo clearly shows the correct electronics recycling bin.",
            audit_image_url: "/api/uploads/recycling-audit/attempt-2.jpg",
          },
          {
            id: 999,
            attempt_no: 2,
            audit_result: "passed",
            audit_reason: "The photo clearly shows the correct electronics recycling bin.",
            audit_image_url: "/api/uploads/recycling-audit/attempt-2.jpg",
          },
        ],
        locked: true,
        submittedImageUrl: "/api/uploads/recycling-audit/attempt-2.jpg",
        feedback: "Audit passed. Your recycling case has been verified, and 4 points were awarded. The photo clearly shows the correct electronics recycling bin.",
      },
    });

    expect(wrapper.text()).toContain("2");
    expect(wrapper.text()).toContain("2/2");
    expect(wrapper.text()).not.toContain("3/3");
  });
});
