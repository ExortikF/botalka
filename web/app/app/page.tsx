import { redirect } from "next/navigation";

/** Отдельной «главной» нет — всё разложено по вкладкам, входная точка кабинета это профиль. */
export default function AppIndex() {
  redirect("/app/profile");
}
