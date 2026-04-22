import { useInfiniteQuery } from "@tanstack/react-query";
import { getDecisions } from "../api/stats";

const DECISIONS_PAGE_SIZE = 20;

export function useInfiniteDecisions() {
  return useInfiniteQuery({
    queryKey: ["decisions-infinite"],
    queryFn: ({ pageParam = 1 }) =>
      getDecisions(pageParam as number, DECISIONS_PAGE_SIZE),
    initialPageParam: 1,
    getNextPageParam: (lastPage) => {
      const fetched = (lastPage.page - 1) * lastPage.page_size + lastPage.items.length;
      return fetched < lastPage.total ? lastPage.page + 1 : undefined;
    },
  });
}
