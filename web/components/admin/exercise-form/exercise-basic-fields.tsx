// ABOUTME: Field group for ExerciseForm — title, description, home-screen toggle, display order.
// ABOUTME: Split out from exercise-form.tsx to keep the parent component under the line cap.

import type { AdminExercise } from "@/types";
import dictionary from "@/dictionaries/en.json";
import { FORM_CHECKBOX_CLASSES, FORM_INPUT_CLASSES, FORM_LABEL_CLASSES, FORM_HELPER_CLASSES } from "../form-field-classes";

const STRINGS = dictionary.admin.forms.exercise;

interface ExerciseBasicFieldsProps {
  exercise?: AdminExercise;
  showOnHomeScreen: boolean;
  onShowOnHomeScreenChange: (value: boolean) => void;
}

export function ExerciseBasicFields({
  exercise,
  showOnHomeScreen,
  onShowOnHomeScreenChange,
}: ExerciseBasicFieldsProps) {
  return (
    <>
      <div>
        <label htmlFor="title" className={FORM_LABEL_CLASSES}>
          {STRINGS.titleLabel}
        </label>
        <input
          id="title"
          name="title"
          type="text"
          required
          defaultValue={exercise?.title}
          className={FORM_INPUT_CLASSES}
          placeholder={STRINGS.titlePlaceholder}
        />
      </div>

      <div>
        <label htmlFor="description" className={FORM_LABEL_CLASSES}>
          {STRINGS.descriptionLabel}
        </label>
        <textarea
          id="description"
          name="description"
          required
          rows={3}
          defaultValue={exercise?.description}
          className={`${FORM_INPUT_CLASSES} leading-relaxed`}
          placeholder={STRINGS.descriptionPlaceholder}
        />
      </div>

      <div>
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            name="showOnHomeScreen"
            value="true"
            checked={showOnHomeScreen}
            onChange={(e) => onShowOnHomeScreenChange(e.target.checked)}
            className={FORM_CHECKBOX_CLASSES}
          />
          <span className="mb-0 text-[0.9375rem] font-medium text-mani-text">
            {STRINGS.showOnHomeScreenLabel}
          </span>
        </label>
        <p className={FORM_HELPER_CLASSES}>{STRINGS.showOnHomeScreenHelper}</p>
      </div>

      <div>
        <label htmlFor="displayOrder" className={FORM_LABEL_CLASSES}>
          {STRINGS.displayOrderLabel}
        </label>
        <input
          id="displayOrder"
          name="displayOrder"
          type="number"
          min={0}
          defaultValue={exercise?.displayOrder ?? 0}
          className={FORM_INPUT_CLASSES}
        />
        <p className={FORM_HELPER_CLASSES}>{STRINGS.displayOrderHelper}</p>
      </div>
    </>
  );
}
