import { useTranslation } from "react-i18next";

export function useGradeLabel(): (grade: string) => string {
  const { t } = useTranslation();
  return (grade: string) => t(`boq.range.grade.${grade}`, grade.replace(/_/g, " ").toLowerCase());
}