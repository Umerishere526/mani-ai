// ABOUTME: Field group for ExerciseForm — the library category and the exercise type.
// ABOUTME: Both lists come from the dictionary, keyed by the values the backend stores.

import type { AdminExercise } from "@/types";
import dictionary from "@/dictionaries/en.json";
import { FORM_INPUT_CLASSES, FORM_LABEL_CLASSES } from "../form-field-classes";

const STRINGS = dictionary.admin.forms.exercise;
const CATEGORIES = Object.entries(dictionary.admin.forms.categories);
const TYPES = Object.entries(dictionary.admin.forms.exerciseTypes);

interface ExerciseClassificationFieldsProps {
  exercise?: AdminExercise;
}

export function ExerciseClassificationFields({ exercise }: ExerciseClassificationFieldsProps) {
  return (
    <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
      <div>
        <label htmlFor="category" className={FORM_LABEL_CLASSES}>
          {STRINGS.categoryLabel}
        </label>
        <select id="category" name="category" required defaultValue={exercise?.category ?? ""} className={FORM_INPUT_CLASSES}>
          <option value="" disabled>
            {STRINGS.categoryPlaceholder}
          </option>
          {CATEGORIES.map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label htmlFor="type" className={FORM_LABEL_CLASSES}>
          {STRINGS.typeLabel}
        </label>
        <select id="type" name="type" required defaultValue={exercise?.type ?? ""} className={FORM_INPUT_CLASSES}>
          <option value="" disabled>
            {STRINGS.typePlaceholder}
          </option>
          {TYPES.map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
