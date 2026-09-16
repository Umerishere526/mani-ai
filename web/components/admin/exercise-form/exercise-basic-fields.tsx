// ABOUTME: Field group for ExerciseForm — title, description, home-screen toggle, category, order.
// ABOUTME: Split out from exercise-form.tsx to keep the parent component under the line cap.

import type { AdminExercise } from "@/types";
import dictionary from "@/dictionaries/en.json";
import { FORM_INPUT_CLASSES, FORM_TEXTAREA_CLASSES, FORM_LABEL_CLASSES, FORM_HELPER_CLASSES } from "../form-field-classes";

const STRINGS = dictionary.admin.forms.exercise;
const CATEGORY_LABELS = dictionary.admin.forms.categories;

const CATEGORIES = Object.entries(CATEGORY_LABELS).map(([value, label]) => ({ value, label }));

interface ExerciseBasicFieldsProps {
  exercise?: AdminExercise;
  showOnHomeScreen: boolean;
  onShowOnHomeScreenChange: (value: boolean) => void;
  isLibraryExercise: boolean;
}

export function ExerciseBasicFields({
  exercise,
  showOnHomeScreen,
  onShowOnHomeScreenChange,
  isLibraryExercise,
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
          className={FORM_TEXTAREA_CLASSES}
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
            className="h-4 w-4 rounded border-mani-border text-mani-accent focus:ring-mani-accent-light"
          />
          <span className="mb-0 text-[0.9375rem] font-medium text-mani-text">
            {STRINGS.showOnHomeScreenLabel}
          </span>
        </label>
        <p className={FORM_HELPER_CLASSES}>{STRINGS.showOnHomeScreenHelper}</p>
      </div>

      {isLibraryExercise && (
        <div>
          <label htmlFor="category" className={FORM_LABEL_CLASSES}>
            {STRINGS.categoryLabel}
          </label>
          <select
            id="category"
            name="category"
            required={isLibraryExercise}
            defaultValue={exercise?.category ?? "Anxiety"}
            className={FORM_INPUT_CLASSES}
          >
            {CATEGORIES.map((cat) => (
              <option key={cat.value} value={cat.value}>
                {cat.label}
              </option>
            ))}
          </select>
        </div>
      )}

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
