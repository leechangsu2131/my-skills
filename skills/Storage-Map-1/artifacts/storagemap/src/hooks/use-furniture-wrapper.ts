import { useQueryClient } from "@tanstack/react-query";
import { 
  useCreateFurniture, 
  useUpdateFurniture, 
  useDeleteFurniture,
  getListFurnitureQueryKey
} from "@workspace/api-client-react";

export function useCreateFurnitureMutation() {
  const queryClient = useQueryClient();
  return useCreateFurniture({
    mutation: {
      onSuccess: (_, variables) => {
        queryClient.invalidateQueries({ queryKey: getListFurnitureQueryKey(variables.spaceId) });
      }
    }
  });
}

export function useUpdateFurnitureMutation(spaceId: string) {
  const queryClient = useQueryClient();
  return useUpdateFurniture({
    mutation: {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: getListFurnitureQueryKey(spaceId) });
      }
    }
  });
}

export function useDeleteFurnitureMutation(spaceId: string) {
  const queryClient = useQueryClient();
  return useDeleteFurniture({
    mutation: {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: getListFurnitureQueryKey(spaceId) });
      }
    }
  });
}
