import { useQueryClient } from "@tanstack/react-query";
import { 
  useCreateSpace, 
  useUpdateSpace, 
  useDeleteSpace,
  getListSpacesQueryKey,
  getGetSpaceQueryKey
} from "@workspace/api-client-react";

export function useCreateSpaceMutation() {
  const queryClient = useQueryClient();
  return useCreateSpace({
    mutation: {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: getListSpacesQueryKey() });
      }
    }
  });
}

export function useUpdateSpaceMutation() {
  const queryClient = useQueryClient();
  return useUpdateSpace({
    mutation: {
      onSuccess: (_, variables) => {
        queryClient.invalidateQueries({ queryKey: getListSpacesQueryKey() });
        queryClient.invalidateQueries({ queryKey: getGetSpaceQueryKey(variables.spaceId) });
      }
    }
  });
}

export function useDeleteSpaceMutation() {
  const queryClient = useQueryClient();
  return useDeleteSpace({
    mutation: {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: getListSpacesQueryKey() });
      }
    }
  });
}
