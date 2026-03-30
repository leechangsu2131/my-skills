import { useQueryClient } from "@tanstack/react-query";
import { 
  useCreateItem, 
  useUpdateItem, 
  useDeleteItem,
  getListItemsQueryKey,
  getListItemsByFurnitureQueryKey,
  getGetItemQueryKey,
  getGetItemHistoryQueryKey
} from "@workspace/api-client-react";

export function useCreateItemMutation(furnitureId?: string) {
  const queryClient = useQueryClient();
  return useCreateItem({
    mutation: {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: getListItemsQueryKey() });
        if (furnitureId) {
          queryClient.invalidateQueries({ queryKey: getListItemsByFurnitureQueryKey(furnitureId) });
        }
      }
    }
  });
}

export function useUpdateItemMutation(furnitureId?: string) {
  const queryClient = useQueryClient();
  return useUpdateItem({
    mutation: {
      onSuccess: (_, variables) => {
        queryClient.invalidateQueries({ queryKey: getListItemsQueryKey() });
        queryClient.invalidateQueries({ queryKey: getGetItemQueryKey(variables.itemId) });
        queryClient.invalidateQueries({ queryKey: getGetItemHistoryQueryKey(variables.itemId) });
        if (furnitureId) {
          queryClient.invalidateQueries({ queryKey: getListItemsByFurnitureQueryKey(furnitureId) });
        }
      }
    }
  });
}

export function useDeleteItemMutation(furnitureId?: string) {
  const queryClient = useQueryClient();
  return useDeleteItem({
    mutation: {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: getListItemsQueryKey() });
        if (furnitureId) {
          queryClient.invalidateQueries({ queryKey: getListItemsByFurnitureQueryKey(furnitureId) });
        }
      }
    }
  });
}
